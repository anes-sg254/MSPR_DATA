import pandas as pd
from sqlalchemy import create_engine

def nettoyer_economie(path, annee, feuille):
    # lire le fichier Excel
    df = pd.read_excel(path, sheet_name=feuille, header=4)

    # récupérer la ligne des codes techniques comme noms de colonnes
    df.columns = df.iloc[0]

    # supprimer cette ligne
    df = df.iloc[1:].copy()

    # garder les colonnes utiles
    df = df[[
        "CODGEO",
        "LIBGEO",
        "NBETAB",
        "INDUS",
        "CONSTR",
        "COM_TRANSP",
        "SERV_TOT",
        "CREATION",
        "AUTO_ENT"
    ]]

    # renommer
    df = df.rename(columns={
        "CODGEO": "code_commune",
        "LIBGEO": "commune",
        "NBETAB": "nb_etablissements",
        "INDUS": "industrie",
        "CONSTR": "construction",
        "COM_TRANSP": "commerce_transport",
        "SERV_TOT": "services_total",
        "CREATION": "creations_etablissements",
        "AUTO_ENT": "micro_entrepreneurs"
    })

    # nettoyer code commune
    df["code_commune"] = df["code_commune"].astype(str).str.strip()

    # filtrer les communes du 62
    df = df[df["code_commune"].str.startswith("62")]

    # convertir les colonnes numériques
    cols_num = [
        "nb_etablissements",
        "industrie",
        "construction",
        "commerce_transport",
        "services_total",
        "creations_etablissements",
        "micro_entrepreneurs"
    ]

    for col in cols_num:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ajouter l'année
    df["annee"] = annee

    # reset index
    df = df.reset_index(drop=True)

    return df


# adapte le nom de feuille selon ton fichier
df2022 = nettoyer_economie("../data/donnes/economie_2022.xlsx", 2022, "COM_2022")

# quand tu auras le 2017, décommente :
df2017 = nettoyer_economie("../data/donnes/economie_2017.xlsx", 2017, "COM_2018")
df_final = pd.concat([df2017, df2022], ignore_index=True)

df_final.to_csv("../data/donnes_clean/economie_clean.csv", index=False)

print(df_final.head())
print(df_final.columns)
print(df_final.shape)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/elections")
df_final.to_sql("economie", engine, if_exists="append", index=False)