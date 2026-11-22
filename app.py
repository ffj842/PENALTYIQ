
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
# ==========================================
# MEMOIRE DES PREDICTIONS PENALTYIQ
# ==========================================

conn.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    team1 TEXT,
    team2 TEXT,
    odds1 REAL,
    odds2 REAL,
    predicted_winner INTEGER,
    confidence REAL,
    actual_winner INTEGER,
    prediction_correct INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    ("match_id", "INTEGER"),
]:
    if nom not in colonnes:
        conn.execute(
            f"ALTER TABLE decoded_sessions ADD COLUMN {nom} {type_colonne}"
        )

conn.commit()

st.divider()
st.header("⚽ Décodeur PENALTYIQ")

matchs_disponibles = conn.execute("""
SELECT id, team_a, team_b, odds_a, odds_b
FROM matches
WHERE status = 'À venir'
ORDER BY id DESC
""").fetchall()

if matchs_disponibles:
    choix_match = st.selectbox(
        "Sélectionne le match à analyser",
        matchs_disponibles,
        format_func=lambda m: (
            f"{m[1]} - {m[2]} | Cotes : {m[3]} / {m[4]}"
        )
    )

    match_id_saisi = choix_match[0]
    equipe1_saisie = choix_match[1]
    equipe2_saisie = choix_match[2]
    cote1_saisie = choix_match[3]
    cote2_saisie = choix_match[4]
else:
    st.warning("Aucun match à venir. Enregistre d'abord un match.")
    match_id_saisi = None

# ==========================================
# MOTEUR DE PREDICTION PENALTYIQ
# ==========================================

if match_id_saisi is not None:

    if st.button("🧠 Prédire le vainqueur"):

        # Probabilités calculées à partir des cotes
        probabilite_cote1 = (1 / cote1_saisie) / (
            (1 / cote1_saisie) + (1 / cote2_saisie)
        )

        # Récupération des anciennes séances terminées
        historique_apprentissage = conn.execute("""
        SELECT
            COUNT(*),
            SUM(CASE WHEN winner = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN winner = 2 THEN 1 ELSE 0 END)
        FROM decoded_sessions
        WHERE winner IN (1, 2)
        """).fetchone()

        nombre_seances = historique_apprentissage[0]
        victoires1 = historique_apprentissage[1] or 0
        victoires2 = historique_apprentissage[2] or 0

        # Estimation historique avec lissage
        probabilite_historique1 = (
            victoires1 + 1
        ) / (nombre_seances + 2)

        # Fiabilité de l'historique
        fiabilite_historique = (
            nombre_seances / (nombre_seances + 10)
        )

        # Combinaison des cotes et de l'historique
        probabilite1 = (
            probabilite_cote1 * (
                1 - 0.25 * fiabilite_historique
            )
            + probabilite_historique1 * (
                0.25 * fiabilite_historique
            )
        )

        probabilite2 = 1 - probabilite1

        prediction = 1 if probabilite1 >= 0.5 else 2

        confiance = max(probabilite1, probabilite2) * 100

        # Enregistrement du pronostic
        conn.execute("""
        INSERT INTO predictions
        (match_id, team1, team2, odds1, odds2,
         predicted_winner, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id_saisi,
            equipe1_saisie,
            equipe2_saisie,
            cote1_saisie,
            cote2_saisie,
            prediction,
            confiance
        ))

        conn.commit()

        nom_prédit = (
            equipe1_saisie if prediction == 1
            else equipe2_saisie
        )

        st.success(f"Pronostic PENALTYIQ : {nom_prédit}")

        st.metric(
            "Indice estimé selon les données disponibles",
            f"{confiance:.1f} %"
        )

        st.write(
            "Séances historiques analysées :",
            nombre_seances
        )

code_saisi = st.text_input(
    "Entre le code de la séance",
    placeholder="Exemple : 12121010"
)



if st.button("Analyser la séance"):
    if match_id_saisi is None:
        st.error("Sélectionne d'abord un match.")
    else:
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
                gagnant = (
                    equipe1_saisie
                    if resultat["winner"] == 1
                    else equipe2_saisie
                )

                st.success(f"🏆 Vainqueur : {gagnant}")

            conn.execute("""
            INSERT INTO decoded_sessions
            (match_id, code, score1, score2, winner, phase,
             team1, team2, odds1, odds2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id_saisi,
                code_saisi.strip(),
                resultat["score1"],
                resultat["score2"],
                resultat["winner"],
                resultat["phase"],
                equipe1_saisie,
                equipe2_saisie,
                cote1_saisie,
                cote2_saisie
            ))

            
            if resultat["winner"]:
                conn.execute("""
                UPDATE matches
                SET winner = ?, status = 'Terminé'
                WHERE id = ?
                """, (gagnant, match_id_saisi))

                # Evaluation des predictions PENALTYIQ
                conn.execute("""
                UPDATE predictions
                SET actual_winner = ?,
                    prediction_correct = CASE
                        WHEN predicted_winner = ? THEN 1
                        ELSE 0
                    END
                WHERE match_id = ?
                  AND actual_winner IS NULL
                """, (
                    resultat["winner"],
                    resultat["winner"],
                    match_id_saisi
                ))

            conn.commit()

            st.success("Résultat enregistré et match mis à jour !")

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

# ==========================================
# PERFORMANCE DU MOTEUR PENALTYIQ
# ==========================================

st.subheader("🧠 Performance des prédictions")

pronostics_total = stats_conn.execute("""
SELECT COUNT(*) FROM predictions
""").fetchone()[0]

pronostics_evalues = stats_conn.execute("""
SELECT COUNT(*) FROM predictions
WHERE actual_winner IS NOT NULL
""").fetchone()[0]

pronostics_corrects = stats_conn.execute("""
SELECT COUNT(*) FROM predictions
WHERE prediction_correct = 1
""").fetchone()[0]

pronostics_incorrects = stats_conn.execute("""
SELECT COUNT(*) FROM predictions
WHERE prediction_correct = 0
""").fetchone()[0]

# ==========================================
# DETECTION DES FAVORIS BATTUS
# ==========================================

surprises = stats_conn.execute("""
SELECT COUNT(*)
FROM decoded_sessions
WHERE winner IN (1, 2)
AND odds1 IS NOT NULL
AND odds2 IS NOT NULL
AND (
    (odds1 < odds2 AND winner = 2)
    OR
    (odds2 < odds1 AND winner = 1)
)
""").fetchone()[0]

st.metric("⚠️ Surprises : favoris battus", surprises)

# ==========================================
# ANALYSE FAVORIS ET OUTSIDERS
# ==========================================

analyse_favoris = stats_conn.execute("""
SELECT
    COUNT(*) AS total,
    SUM(CASE
        WHEN (odds1 < odds2 AND winner = 1)
          OR (odds2 < odds1 AND winner = 2)
        THEN 1 ELSE 0 END) AS favoris_gagnants,
    SUM(CASE
        WHEN (odds1 < odds2 AND winner = 2)
          OR (odds2 < odds1 AND winner = 1)
        THEN 1 ELSE 0 END) AS outsiders_gagnants
FROM decoded_sessions
WHERE winner IN (1, 2)
AND odds1 IS NOT NULL
AND odds2 IS NOT NULL
AND odds1 != odds2
""").fetchone()

total_analyses = analyse_favoris[0]
favoris_gagnants = analyse_favoris[1] or 0
outsiders_gagnants = analyse_favoris[2] or 0

taux_surprises = (
    outsiders_gagnants / total_analyses * 100
    if total_analyses > 0 else 0
)

# ==========================================
# ANALYSE DES SURPRISES PAR TRANCHE DE COTES
# ==========================================

analyse_tranches = stats_conn.execute("""
SELECT
    CASE
        WHEN MIN(odds1, odds2) < 1.50 THEN 'Moins de 1.50'
        WHEN MIN(odds1, odds2) < 2.00 THEN '1.50 à 1.99'
        WHEN MIN(odds1, odds2) < 2.50 THEN '2.00 à 2.49'
        ELSE '2.50 et plus'
    END AS tranche,

    COUNT(*) AS matchs,

    SUM(CASE
        WHEN (odds1 < odds2 AND winner = 2)
          OR (odds2 < odds1 AND winner = 1)
        THEN 1 ELSE 0
    END) AS surprises

FROM decoded_sessions

WHERE winner IN (1, 2)
AND odds1 IS NOT NULL
AND odds2 IS NOT NULL
AND odds1 != odds2

GROUP BY tranche
""").fetchall()

st.subheader("🔎 Surprises selon les cotes du favori")

if analyse_tranches:
    df_tranches = pd.DataFrame(
        analyse_tranches,
        columns=["Tranche de cote", "Matchs", "Surprises"]
    )

    df_tranches["Taux de surprises"] = (
        df_tranches["Surprises"]
        / df_tranches["Matchs"] * 100
    ).round(1).astype(str) + " %"

    st.dataframe(df_tranches, use_container_width=True)
else:
    st.info("Pas encore assez de résultats enregistrés.")

st.subheader("📊 Analyse des favoris et outsiders")

f1, f2, f3 = st.columns(3)

f1.metric("🏆 Favoris gagnants", favoris_gagnants)
f2.metric("⚠️ Outsiders gagnants", outsiders_gagnants)
f3.metric("📈 Taux de surprises", f"{taux_surprises:.1f} %")

taux_reussite = (
    pronostics_corrects / pronostics_evalues * 100
    if pronostics_evalues > 0 else 0
)

p1, p2, p3, p4 = st.columns(4)

with p1:
    st.metric("Pronostics totaux", pronostics_total)

with p2:
    st.metric("Pronostics corrects", pronostics_corrects)

with p3:
    st.metric("Pronostics incorrects", pronostics_incorrects)

with p4:
    st.metric("Taux de réussite", f"{taux_reussite:.1f} %")

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
