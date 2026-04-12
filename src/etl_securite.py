import pandas as pd
import numpy as np
from sqlalchemy import create_engine

df = pd.read_csv(
    "../data/donnes/securite.csv",
    sep=";",
    low_memory=False
)


df = df.rename(columns={
    "CODGEO_2025": "code_commune",
    
})


df["code_commune"] = df["code_commune"].astype(str).str.strip()

df = df[df["code_commune"].str.startswith("62")]


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


df = df[df["annee"].isin([2017, 2022])]


# df = df.dropna(subset=["taux"])


df = df[[
    "code_commune",
    "annee",
    "indicateur",
    "nombre",
    "taux"
]]

print(df.head())
print(df.shape)

df.to_csv("../data/donnes_clean/securite_clean.csv", index=False)


engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/elections")
df.to_sql("securite", engine, if_exists="append", index=False)