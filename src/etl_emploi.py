import pandas as pd
from sqlalchemy import create_engine

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

df = df[df["Code département"] == "62"]

df = df[df["Sexe"] == "Total"]


df = df[df["annee"].isin([2017, 2022])]

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

df = df.groupby(
    ["code_commune", "annee", "tranche_age"],
    as_index=False
)["demandeurs_emploi"].sum()

print(df.head())
print(df.shape)

df.to_csv("../data/donnes_clean/emploi_clean.csv", index=False)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/elections")
df.to_sql("emploi", engine, if_exists="append", index=False)