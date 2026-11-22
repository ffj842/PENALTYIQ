
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


st.divider()
st.header("⚽ Décodeur PENALTYIQ")

code_saisi = st.text_input(
    "Entre le code de la séance",
    placeholder="Exemple : 12121010"
)

if st.button("Analyser la séance"):
    resultat = penaltyiq_decode(code_saisi)

    if "error" in resultat:
        st.error(resultat["error"])
    else:
        st.subheader("Résultat de l'analyse")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Équipe 1", resultat["score1"])

        with col2:
            st.metric("Équipe 2", resultat["score2"])

        st.write("Phase :", resultat["phase"])
        st.write("Statut :", resultat["statut"])

        if resultat["winner"]:
            st.success(
                f"🏆 L'équipe {resultat['winner']} a gagné !"
            )
