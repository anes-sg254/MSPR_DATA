import pandas as pd
from sqlalchemy import create_engine

def nettoyer_demographie(path, annee, feuille):
    
    df = pd.read_excel(path, sheet_name=feuille, header=4)

    df.columns = df.iloc[0]

    
    df = df.iloc[1:].copy()

    
    df = df[[
        "CODGEO",
        "LIBGEO",
        "POP_MUN",
        "TX_TOT_0A24",
        "TX_TOT_60ETPLUS",
        "IND_JEUNE"
    ]]

    
    df = df.rename(columns={
        "CODGEO": "code_commune",
        "LIBGEO": "commune",
        "POP_MUN": "population",
        "TX_TOT_0A24": "part_jeunes",
        "TX_TOT_60ETPLUS": "part_seniors",
        "IND_JEUNE": "indice_jeunesse"
    })

   
    df = df[df["code_commune"].astype(str).str.startswith("62")]

  
    df["annee"] = annee

    df = df.reset_index(drop=True)

    return df


df2017 = nettoyer_demographie("../data/donnes/demographie_2017.xls", 2017, "COM")
df2022 = nettoyer_demographie("../data/donnes/demographie_2022.xls", 2022, "COM_2021")

df_final = pd.concat([df2017, df2022], ignore_index=True)

df_final.to_csv("../data/donnes_clean/demographie_clean.csv", index=False)

print(df_final.head())
print(df_final.columns)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/elections")
df_final.to_sql("demographie", engine, if_exists="append", index=False)