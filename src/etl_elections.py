import pandas as pd
from sqlalchemy import create_engine

def nettoyer_elections(path, annee):
    df = pd.read_csv(
        path,
        sep=";",
        dtype={
            "code_departement": str,
            "code_commune": str,
            "code_bv": str
        },
        low_memory=False
    )

    # filtrer le département 62
    df = df[df["code_commune"].astype(str).str.startswith("62")]

    # garder les colonnes utiles
    df = df[[
        "code_commune",
        "libelle_commune",
        "inscrits",
        "abstentions",
        "votants",
        "blancs",
        "nuls",
        "exprimes"
    ]]

    # convertir en numérique
    cols_num = ["inscrits", "abstentions", "votants", "blancs", "nuls", "exprimes"]
    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # agréger par commune
    df = df.groupby(
        ["code_commune", "libelle_commune"],
        as_index=False
    )[cols_num].sum()

    # ajouter l'année
    df["annee"] = annee

    # calcul du taux d'abstention
    df["taux_abstention"] = (df["abstentions"] / df["inscrits"]) * 100

    # renommer commune pour homogénéité
    df = df.rename(columns={"libelle_commune": "commune"})

    return df


df2017 = nettoyer_elections("../data/donnes/elections_2017.csv", 2017)
df2022 = nettoyer_elections("../data/donnes/elections_2022.csv", 2022)

df_final = pd.concat([df2017, df2022], ignore_index=True)

df_final.to_csv("../data/donnes_clean/abstention_clean.csv", index=False)

print(df_final.head())
print(df_final["annee"].value_counts())
print(df_final.shape)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/elections")
df_final.to_sql("elections", engine, if_exists="append", index=False)