import pandas as pd
from sqlalchemy import create_engine
from db_utils import get_engine

def nettoyer_communes(path, feuille):
    df = pd.read_excel(path, sheet_name=feuille, header=4)

    df.columns = df.iloc[0]
    df = df.iloc[1:].copy()

    df = df[[
        "CODGEO",
        "LIBGEO"
    ]]

    df = df.rename(columns={
        "CODGEO": "code_commune",
        "LIBGEO": "commune"
    })

    df["code_commune"] = df["code_commune"].astype(str)
    df["commune"] = df["commune"].astype(str).str.strip()

    df = df[df["code_commune"].str.startswith("33")]

   
    df = df.drop_duplicates(subset=["code_commune", "commune"])

    return df.reset_index(drop=True)


df_communes = nettoyer_communes("../data/donnes/economie_2.xlsx", "COM")

df_communes.to_csv("../data/donnes_clean/communes_clean.csv", index=False)

print(df_communes.head())
print(df_communes.shape)

engine = get_engine()
df_communes.to_sql("commune", engine, if_exists="append", index=False)