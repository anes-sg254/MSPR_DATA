import pandas as pd
from sqlalchemy import create_engine
from db_utils import get_engine

df = pd.read_csv(
    "../data/donnes/emploi_commune.csv",
    sep=";",
    dtype={
        "Code département": str,
        "Code commune": str
    },
    low_memory=False
)


for col in ["Date", "Code département", "Code commune", "Sexe", "Tranche d'âge"]:
    df[col] = df[col].astype(str).str.strip()


df["annee"] = df["Date"].str.split("-").str[0].astype(int)


df = df[df["Code département"] == "33"]


df = df[df["Sexe"] == "Total"]


df = df[df["annee"] == 2022]

df = df[[
    "Code commune",
    "annee",
    "Tranche d'âge",
    "Nombre de demandeurs d'emploi"
]]


df = df.rename(columns={
    "Code commune": "code_commune",
    "Tranche d'âge": "tranche_age",
    "Nombre de demandeurs d'emploi": "demandeurs_emploi"
})


df["demandeurs_emploi"] = pd.to_numeric(df["demandeurs_emploi"], errors="coerce")


df = df.groupby(
    ["code_commune", "annee", "tranche_age"],
    as_index=False
)["demandeurs_emploi"].sum()


df = df.pivot(
    index=["code_commune", "annee"],
    columns="tranche_age",
    values="demandeurs_emploi"
).reset_index()


df = df.rename(columns={
    "Total": "emploi_total",
    "Moins de 25 ans": "emploi_moins_25",
    "De 25 à 49 ans": "emploi_25_49",
    "50 ans et plus": "emploi_50_plus"
})


for col in ["emploi_total", "emploi_moins_25", "emploi_25_49", "emploi_50_plus"]:
    if col not in df.columns:
        df[col] = 0
    df[col] = df[col].fillna(0).astype(int)


df = df[[
    "code_commune",
    "annee",
    "emploi_total",
    "emploi_moins_25",
    "emploi_25_49",
    "emploi_50_plus"
]]

print(df.head())
print(df.shape)

df.to_csv("../data/donnes_clean/emploi_clean.csv", index=False)

engine = get_engine()
df.to_sql("donnees_emploi", engine, if_exists="append", index=False)