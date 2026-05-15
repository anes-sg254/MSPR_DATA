import pandas as pd
from sqlalchemy import create_engine
from db_utils import get_engine

def nettoyer_participation(path, id_election):
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

    
    df["code_commune"] = df["code_commune"].astype(str).str.strip().str.zfill(5)
    df = df[df["code_commune"].str.startswith("33")]

    
    df = df[[
        "code_commune",
        "inscrits",
        "abstentions",
        "votants",
        "blancs",
        "nuls",
        "exprimes"
    ]]

    
    cols_num = ["inscrits", "abstentions", "votants", "blancs", "nuls", "exprimes"]
    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    
    df = df.groupby("code_commune", as_index=False)[cols_num].sum()

    
    df["id_election"] = id_election

    df["taux_abstention"] = (df["abstentions"] / df["inscrits"]) * 100

   
    df = df[[
        "code_commune",
        "id_election",
        "inscrits",
        "abstentions",
        "votants",
        "blancs",
        "nuls",
        "exprimes",
        "taux_abstention"
    ]]

    return df


df_participation = nettoyer_participation(
    "../data/donnes/elections_2022.csv",
    id_election=1
)

print(df_participation.head())
print(df_participation.shape)

df_participation.to_csv("../data/donnes_clean/participation_2022_clean.csv", index=False)

engine =get_engine()
df_participation.to_sql("participation", engine, if_exists="append", index=False)