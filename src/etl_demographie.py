import pandas as pd
from sqlalchemy import create_engine

def nettoyer_demographie(path, annee, feuille, cols_source):
    df = pd.read_excel(path, sheet_name=feuille, header=4)

    df.columns = df.iloc[0]
    df = df.iloc[1:].copy()

    df = df[[
        "CODGEO",
        "LIBGEO",
        cols_source["population"],
        cols_source["pop_0_14"],
        cols_source["pop_15_29"],
        cols_source["pop_60_74"],
        cols_source["pop_75_89"],
        cols_source["pop_90_plus"]
    ]]

    df = df.rename(columns={
        "CODGEO": "code_commune",
        "LIBGEO": "commune",
        cols_source["population"]: "population",
        cols_source["pop_0_14"]: "pop_0_14",
        cols_source["pop_15_29"]: "pop_15_29",
        cols_source["pop_60_74"]: "pop_60_74",
        cols_source["pop_75_89"]: "pop_75_89",
        cols_source["pop_90_plus"]: "pop_90_plus"
    })

    df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)
    df = df[df["code_commune"].str.startswith("31")]

    cols_num = [
        "population",
        "pop_0_14",
        "pop_15_29",
        "pop_60_74",
        "pop_75_89",
        "pop_90_plus"
    ]

    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["part_jeunes"] = ((df["pop_0_14"] + df["pop_15_29"]) / df["population"]) * 100
    df["part_seniors"] = ((df["pop_60_74"] + df["pop_75_89"] + df["pop_90_plus"]) / df["population"]) * 100

    denom = df["pop_60_74"] + df["pop_75_89"] + df["pop_90_plus"]
    df["indice_jeunesse"] = ((df["pop_0_14"] + df["pop_15_29"]) / denom.replace(0, pd.NA))

    df["annee"] = annee

    df = df[[
        "code_commune",
        "commune",
        "population",
        "part_jeunes",
        "part_seniors",
        "indice_jeunesse",
        "annee"
    ]]

    return df.reset_index(drop=True)


cols_2022 = {
    "population": "P22_POP",
    "pop_0_14": "P22_POP0014",
    "pop_15_29": "P22_POP1529",
    "pop_60_74": "P22_POP6074",
    "pop_75_89": "P22_POP7589",
    "pop_90_plus": "P22_POP90P"
}

df2022 = nettoyer_demographie("../data/donnes/demographie_2_2022.xlsx", 2022, "COM_2022", cols_2022)

df2022.to_csv("../data/donnes_clean/demographie2_clean.csv", index=False)

print(df2022.head())
print(df2022["annee"].value_counts())
print(df2022.shape)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/mspr_data_final")
df2022.to_sql("donnees_demographie", engine, if_exists="append", index=False)