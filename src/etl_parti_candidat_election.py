import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/mspr_data_final")

df_parti = pd.DataFrame([
    {"id_parti": 1, "nom_parti": "extreme_gauche"},
    {"id_parti": 2, "nom_parti": "gauche"},
    {"id_parti": 3, "nom_parti": "centre"},
    {"id_parti": 4, "nom_parti": "droite"},
    {"id_parti": 5, "nom_parti": "extreme_droite"}
])


df_candidat = pd.DataFrame([
    {"id_candidat": 1, "nom": "ARTHAUD", "prenom": "Nathalie", "id_parti": 1},
    {"id_candidat": 2, "nom": "POUTOU", "prenom": "Philippe", "id_parti": 1},
    {"id_candidat": 3, "nom": "ROUSSEL", "prenom": "Fabien", "id_parti": 2},
    {"id_candidat": 4, "nom": "HIDALGO", "prenom": "Anne", "id_parti": 2},
    {"id_candidat": 5, "nom": "JADOT", "prenom": "Yannick", "id_parti": 2},
    {"id_candidat": 6, "nom": "MÉLENCHON", "prenom": "Jean-Luc", "id_parti": 2},
    {"id_candidat": 7, "nom": "MACRON", "prenom": "Emmanuel", "id_parti": 3},
    {"id_candidat": 8, "nom": "PÉCRESSE", "prenom": "Valérie", "id_parti": 4},
    {"id_candidat": 9, "nom": "LASSALLE", "prenom": "Jean", "id_parti": 4},
    {"id_candidat": 10, "nom": "DUPONT-AIGNAN", "prenom": "Nicolas", "id_parti": 4},
    {"id_candidat": 11, "nom": "LE PEN", "prenom": "Marine", "id_parti": 5},
    {"id_candidat": 12, "nom": "ZEMMOUR", "prenom": "Éric", "id_parti": 5}
])

df_election = pd.DataFrame([
    {"id_election": 1, "annee": 2022, "type_election": "presidentielle_t1"}
])

df_parti.to_sql("parti", engine, if_exists="append", index=False)
df_candidat.to_sql("candidat", engine, if_exists="append", index=False)
df_election.to_sql("election", engine, if_exists="append", index=False)