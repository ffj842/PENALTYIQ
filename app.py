
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="PENALTYIQ",
    page_icon="⚽",
    layout="wide"
)

st.title("🧠 PENALTYIQ")
st.subheader("FIFA PENALTY 23 — Data Collection")

# Connexion à la base de données
conn = sqlite3.connect(
    "penaltyiq.db",
    check_same_thread=False
)

conn.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    team_a TEXT,
    team_b TEXT,
    odds_a REAL,
    odds_b REAL,
    winner TEXT
)
""")

# Ajouter le statut si la colonne n'existe pas encore
columns = [
    row[1] for row in
    conn.execute("PRAGMA table_info(matches)").fetchall()
]

if "status" not in columns:
    conn.execute(
        "ALTER TABLE matches ADD COLUMN status TEXT DEFAULT 'À venir'"
    )

conn.commit()

# Tableau de bord
st.header("📊 Tableau de bord")

total = conn.execute(
    "SELECT COUNT(*) FROM matches"
).fetchone()[0]

upcoming = conn.execute(
    "SELECT COUNT(*) FROM matches WHERE status = 'À venir'"
).fetchone()[0]

finished = conn.execute(
    "SELECT COUNT(*) FROM matches WHERE status = 'Terminé'"
).fetchone()[0]

col1, col2, col3 = st.columns(3)

col1.metric("Matchs enregistrés", total)
col2.metric("Matchs à venir", upcoming)
col3.metric("Matchs terminés", finished)

st.divider()

# Formulaire d'enregistrement
st.header("➕ Enregistrer un match")

with st.form("match_form"):

    match_date = st.date_input(
        "Date du match",
        value=date.today()
    )

    team_a = st.text_input("Participant A")
    team_b = st.text_input("Participant B")

    col1, col2 = st.columns(2)

    with col1:
        odds_a = st.number_input(
            "Cote du participant A",
            min_value=0.0,
            value=1.0,
            step=0.01
        )

    with col2:
        odds_b = st.number_input(
            "Cote du participant B",
            min_value=0.0,
            value=1.0,
            step=0.01
        )

    status = st.selectbox(
        "Statut du match",
        ["À venir", "Terminé"]
    )

    winner = None

    if status == "Terminé":
        winner = st.selectbox(
            "Vainqueur",
            ["Participant A", "Participant B"]
        )

    submitted = st.form_submit_button(
        "Enregistrer le match"
    )

    if submitted:

        if not team_a.strip() or not team_b.strip():
            st.error("Renseigne les deux participants.")

        elif team_a.strip().lower() == team_b.strip().lower():
            st.error("Les deux participants doivent être différents.")

        elif odds_a <= 0 or odds_b <= 0:
            st.error("Les deux cotes doivent être supérieures à zéro.")

        else:
            if winner == "Participant A":
                winner = team_a.strip()
            elif winner == "Participant B":
                winner = team_b.strip()

            conn.execute("""
                INSERT INTO matches
                (date, team_a, team_b, odds_a, odds_b, winner, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                match_date.isoformat(),
                team_a.strip(),
                team_b.strip(),
                odds_a,
                odds_b,
                winner,
                status
            ))

            conn.commit()
            st.success("Match enregistré avec succès !")
            st.rerun()

st.divider()

# Historique
st.header("📚 Historique des matchs")

df = pd.read_sql_query(
    """
    SELECT date, team_a, team_b, odds_a, odds_b, winner, status
    FROM matches
    ORDER BY date DESC, id DESC
    """,
    conn
)

if not df.empty:
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Télécharger les données CSV",
        data=csv,
        file_name="penaltyiq_matches.csv",
        mime="text/csv"
    )
else:
    st.info("Aucun match enregistré pour le moment.")

conn.close()
# ==========================================
# PENALTYIQ - DECODEUR DES TIRS AU BUT
# ==========================================

def penaltyiq_decode(code):
    code = "".join(code.split())

    if not code:
        return {"error": "Entre un code pour commencer."}

    if any(c not in "012" for c in code):
        return {"error": "Le code doit contenir uniquement 0, 1 et 2."}

    score1 = 0
    score2 = 0
    winner = None
    phase = "Première série"

    for i, chiffre in enumerate(code):
        equipe = 1 if i % 2 == 0 else 2

        if chiffre == "1" and equipe != 1:
            return {"error": f"Erreur au tir numéro {i+1} : l'équipe 2 doit être représentée par 2 ou 0."}

        if chiffre == "2" and equipe != 2:
            return {"error": f"Erreur au tir numéro {i+1} : l'équipe 1 doit être représentée par 1 ou 0."}

        if chiffre != "0":
            if equipe == 1:
                score1 += 1
            else:
                score2 += 1

        # Vérification après chaque paire complète
        if i % 2 == 1:
            paire = (i + 1) // 2

            if paire <= 5:
                restant = 5 - paire

                if score1 > score2 + restant:
                    winner = 1
                    break

                if score2 > score1 + restant:
                    winner = 2
                    break

                if paire == 5:
                    if score1 > score2:
                        winner = 1
                    elif score2 > score1:
                        winner = 2
                    else:
                        phase = "Mort subite"

            else:
                phase = "Mort subite"

                tir1 = code[i - 1]
                tir2 = code[i]

                # 1 contre 0 : équipe 1 gagne
                if tir1 == "1" and tir2 == "0":
                    winner = 1

                # 0 contre 2 : équipe 2 gagne
                elif tir1 == "0" and tir2 == "2":
                    winner = 2

    if winner:
        statut = f"Équipe {winner} gagnante"
    elif len(code) < 10:
        statut = "Séance en cours"
    elif len(code) == 10 and score1 == score2:
        statut = "Égalité - mort subite à venir"
    elif len(code) > 10 and len(code) % 2 == 1:
        statut = "En attente du tir de l'équipe 2"
    else:
        statut = "Mort subite en cours"

    return {
        "score1": score1,
        "score2": score2,
        "winner": winner,
        "phase": phase,
        "statut": statut
    }


# ==========================================
# HISTORIQUE DES SEANCES PENALTYIQ
# ==========================================

import sqlite3

conn = sqlite3.connect("penaltyiq.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS decoded_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    code TEXT NOT NULL,
    score1 INTEGER,
    score2 INTEGER,
    winner INTEGER,
    phase TEXT
)
""")

conn.commit()

# Ajouter les colonnes des équipes et des cotes si elles n'existent pas
colonnes = [ligne[1] for ligne in conn.execute(
    "PRAGMA table_info(decoded_sessions)"
).fetchall()]

for nom, type_colonne in [
    ("team1", "TEXT"),
    ("team2", "TEXT"),
    ("odds1", "REAL"),
    ("odds2", "REAL"),
]:
    if nom not in colonnes:
        conn.execute(
            f"ALTER TABLE decoded_sessions ADD COLUMN {nom} {type_colonne}"
        )

conn.commit()

st.divider()
st.header("⚽ Décodeur PENALTYIQ")
equipe1_saisie = st.text_input("Nom de l'équipe 1", key="decode_team1")
equipe2_saisie = st.text_input("Nom de l'équipe 2", key="decode_team2")

cote1_saisie = st.text_input("Cote équipe 1", placeholder="Ex. 1.65")
cote2_saisie = st.text_input("Cote équipe 2", placeholder="Ex. 2.10")
code_saisi = st.text_input(
    "Entre le code de la séance",
    placeholder="Exemple : 12121010"
)


if st.button("Analyser la séance"):
    resultat = penaltyiq_decode(code_saisi)

    if "error" in resultat:
        st.error(resultat["error"])

    else:
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Équipe 1", resultat["score1"])

        with col2:
            st.metric("Équipe 2", resultat["score2"])

        st.write("Phase :", resultat["phase"])
        st.write("Statut :", resultat["statut"])

        if resultat["winner"]:
            st.success(
                f"🏆 Équipe {resultat['winner']} gagnante !"
            )

        conn.execute("""
        INSERT INTO decoded_sessions
        (code, score1, score2, winner, phase, team1, team2, odds1, odds2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code_saisi.strip(),
            resultat["score1"],
            resultat["score2"],
            resultat["winner"],
            resultat["phase"],
            equipe1_saisie.strip(),
            equipe2_saisie.strip(),
            float(cote1_saisie.replace(",", ".")) if cote1_saisie.strip() else None,
            float(cote2_saisie.replace(",", ".")) if cote2_saisie.strip() else None
        ))

        conn.commit()
        st.success("Séance enregistrée dans l'historique !")
        st.write("Vérification :", conn.execute("SELECT COUNT(*) FROM decoded_sessions").fetchone()[0])


historique = conn.execute("""
SELECT created_at, code, score1, score2, winner, phase, team1, team2, odds1, odds2
FROM decoded_sessions
ORDER BY id DESC
""").fetchall()

if historique:
    st.write("TEST : le tableau contient", len(historique), "séances")
   
    df_historique = pd.DataFrame(
        historique,
        columns=[
            "Date",
            "Code",
            "Score équipe 1",
            "Score équipe 2",
            "Vainqueur",
            "Phase",
            "Équipe 1",
            "Équipe 2",
            "Cote équipe 1",
            "Cote équipe 2"
        ]
    )

    st.dataframe(
        df_historique,
        use_container_width=True
    )
else:
    st.info("Aucune séance enregistrée pour le moment.")


conn.close()

# ==========================================
# STATISTIQUES PENALTYIQ
# ==========================================

st.divider()
st.header("📊 Statistiques PENALTYIQ")

stats_conn = sqlite3.connect("penaltyiq.db")

total = stats_conn.execute("""
SELECT COUNT(*) FROM decoded_sessions
""").fetchone()[0]

victoires = stats_conn.execute("""
SELECT winner, COUNT(*)
FROM decoded_sessions
WHERE winner IS NOT NULL
GROUP BY winner
""").fetchall()

moyennes = stats_conn.execute("""
SELECT AVG(score1), AVG(score2)
FROM decoded_sessions
""").fetchone()

scores = stats_conn.execute("""
SELECT score1, score2, COUNT(*)
FROM decoded_sessions
GROUP BY score1, score2
ORDER BY COUNT(*) DESC
""").fetchall()
st.write("Nombre de séances récupérées par l'historique :", len(historique))
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Séances enregistrées", total)

with col2:
    equipe1 = sum(n for e, n in victoires if e == 1)
    st.metric("Victoires équipe 1", equipe1)

with col3:
    equipe2 = sum(n for e, n in victoires if e == 2)
    st.metric("Victoires équipe 2", equipe2)

if total > 0:
    st.subheader("Moyenne des buts")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Équipe 1", round(moyennes[0], 2))

    with c2:
        st.metric("Équipe 2", round(moyennes[1], 2))

    st.subheader("Scores les plus fréquents")

    st.dataframe(
        scores,
        use_container_width=True
    )

else:
    st.info("Ajoute des séances pour afficher les statistiques.")

stats_conn.close()
