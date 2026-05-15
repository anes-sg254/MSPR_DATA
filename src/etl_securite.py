import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from db_utils import get_engine

df = pd.read_csv(
    "../data/donnes/securite.csv",
    sep=";",
    low_memory=False
)


df = df.rename(columns={
    "CODGEO_2025": "code_commune"
})

df["code_commune"] = df["code_commune"].astype(str).str.strip()
df["indicateur"] = df["indicateur"].astype(str).str.strip()


df = df[df["code_commune"].str.startswith("33")]


df["taux_pour_mille"] = df["taux_pour_mille"].replace("NA", np.nan)
df["complement_info_taux"] = df["complement_info_taux"].replace("NA", np.nan)
df["nombre"] = df["nombre"].replace("NA", np.nan)
df["insee_pop"] = df["insee_pop"].replace("NA", np.nan)

df["taux_pour_mille"] = df["taux_pour_mille"].astype(str).str.replace(",", ".", regex=False)
df["complement_info_taux"] = df["complement_info_taux"].astype(str).str.replace(",", ".", regex=False)

df["taux_pour_mille"] = pd.to_numeric(df["taux_pour_mille"], errors="coerce")
df["complement_info_taux"] = pd.to_numeric(df["complement_info_taux"], errors="coerce")
df["nombre"] = pd.to_numeric(df["nombre"], errors="coerce")
df["insee_pop"] = pd.to_numeric(df["insee_pop"], errors="coerce")


df["taux"] = df["taux_pour_mille"].fillna(df["complement_info_taux"])


df["nombre_estime"] = (df["taux"] * df["insee_pop"]) / 1000
df["nombre"] = df["nombre"].fillna(df["nombre_estime"])


df["nombre"] = df["nombre"].round(0)


df = df[df["annee"] == 2022]

df = df[[
    "code_commune",
    "annee",
    "indicateur",
    "nombre"
]]


df = df.groupby(
    ["code_commune", "annee", "indicateur"],
    as_index=False
)["nombre"].sum()


df = df.pivot(
    index=["code_commune", "annee"],
    columns="indicateur",
    values="nombre"
).reset_index()

df = df.rename(columns={
    "Violences physiques intrafamiliales": "violences_intrafamiliales",
    "Violences physiques hors cadre familial": "violences_hors_famille",
    "Violences sexuelles": "violences_sexuelles",
    "Vols avec armes": "vols_avec_armes",
    "Vols violents sans arme": "vols_violents_sans_arme",
    "Vols sans violence contre des personnes": "vols_sans_violence_personnes",
    "Cambriolages de logement": "cambriolages_logement",
    "Vols de véhicule": "vols_vehicule",
    "Vols dans les véhicules": "vols_dans_vehicules",
    "Vols d'accessoires sur véhicules": "vols_accessoires_vehicules",
    "Destructions et dégradations volontaires": "degradations_volontaires",
    "Usage de stupéfiants": "usage_stupefiants"
})


colonnes_attendues = [
    "violences_intrafamiliales",
    "violences_hors_famille",
    "violences_sexuelles",
    "vols_avec_armes",
    "vols_violents_sans_arme",
    "vols_sans_violence_personnes",
    "cambriolages_logement",
    "vols_vehicule",
    "vols_dans_vehicules",
    "vols_accessoires_vehicules",
    "degradations_volontaires",
    "usage_stupefiants"
]

for col in colonnes_attendues:
    if col not in df.columns:
        df[col] = 0
    df[col] = df[col].fillna(0).astype(int)

df = df[[
    "code_commune",
    "annee",
    "violences_intrafamiliales",
    "violences_hors_famille",
    "violences_sexuelles",
    "vols_avec_armes",
    "vols_violents_sans_arme",
    "vols_sans_violence_personnes",
    "cambriolages_logement",
    "vols_vehicule",
    "vols_dans_vehicules",
    "vols_accessoires_vehicules",
    "degradations_volontaires",
    "usage_stupefiants"
]]

print(df.head())
print(df.shape)

df.to_csv("../data/donnes_clean/securite_clean.csv", index=False)

engine = get_engine()
df.to_sql("donnees_securite", engine, if_exists="append", index=False)