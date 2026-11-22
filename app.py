
import streamlit as st
import sqlite3
import pandas as pd

# CONFIGURATION PENALTYIQ
st.set_page_config(
    page_title="PENALTYIQ",
    page_icon="⚽",
    layout="wide"
)

st.title("🧠 PENALTYIQ")
st.subheader("FIFA PENALTY 23 — Prediction Engine")

st.write(
    "Bienvenue dans PENALTYIQ, "
    "notre système d'analyse statistique des matchs."
)

# BASE DE DONNÉES
conn = sqlite3.connect("penaltyiq.db", check_same_thread=False)

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

conn.commit()

st.success("Base de données initialisée.")

# TABLEAU DE BORD
st.subheader("Tableau de bord")

total = conn.execute(
    "SELECT COUNT(*) FROM matches"
).fetchone()[0]

col1, col2, col3 = st.columns(3)

col1.metric("Matchs enregistrés", total)
col2.metric("Prédictions", 0)
col3.metric("Taux de réussite", "En attente")

st.info(
    "Le moteur prédictif sera développé "
    "à partir des historiques réels."
)
