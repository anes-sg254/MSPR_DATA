import pandas as pd
from sqlalchemy import create_engine

def nettoyer_economie(path, annee, feuille, cols_source):
    df = pd.read_excel(path, sheet_name=feuille, header=4)

    df.columns = df.iloc[0]
    df = df.iloc[1:].copy()

    df = df[[
        "CODGEO",
        "LIBGEO",
        cols_source["total"],
        cols_source["industrie"],
        cols_source["construction"],
        cols_source["commerce_transport"],
        cols_source["info_com"],
        cols_source["finance"],
        cols_source["immo"],
        cols_source["services_admin"],
        cols_source["adm_sante_social"],
        cols_source["autres_services"]
    ]]

    df = df.rename(columns={
        "CODGEO": "code_commune",
        "LIBGEO": "commune",
        cols_source["total"]: "creations_total",
        cols_source["industrie"]: "creations_industrie",
        cols_source["construction"]: "creations_construction",
        cols_source["commerce_transport"]: "creations_commerce_transport",
        cols_source["info_com"]: "creations_info_com",
        cols_source["finance"]: "creations_finance",
        cols_source["immo"]: "creations_immo",
        cols_source["services_admin"]: "creations_services_admin",
        cols_source["adm_sante_social"]: "creations_adm_sante_social",
        cols_source["autres_services"]: "creations_autres_services"
    })

    df["code_commune"] = df["code_commune"].astype(str).str.strip().str.zfill(5)
    df = df[df["code_commune"].str.startswith("31")]

    cols_num = [
        "creations_total",
        "creations_industrie",
        "creations_construction",
        "creations_commerce_transport",
        "creations_info_com",
        "creations_finance",
        "creations_immo",
        "creations_services_admin",
        "creations_adm_sante_social",
        "creations_autres_services"
    ]

    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["annee"] = annee

    df = df[[
        "code_commune",
        "commune",
        "creations_total",
        "creations_industrie",
        "creations_construction",
        "creations_commerce_transport",
        "creations_info_com",
        "creations_finance",
        "creations_immo",
        "creations_services_admin",
        "creations_adm_sante_social",
        "creations_autres_services",
        "annee"
    ]]

    return df.reset_index(drop=True)


cols_2022 = {
    "total": "ETCTOT22",
    "industrie": "ETCBE22",
    "construction": "ETCFZ22",
    "commerce_transport": "ETCGI22",
    "info_com": "ETCJZ22",
    "finance": "ETCKZ22",
    "immo": "ETCLZ22",
    "services_admin": "ETCMN22",
    "adm_sante_social": "ETCOQ22",
    "autres_services": "ETCRU22"
}

df2022 = nettoyer_economie("../data/donnes/economie_2.xlsx", 2022, "COM", cols_2022)

df2022.to_csv("../data/donnes_clean/economie_clean.csv", index=False)

print(df2022.head())
print(df2022["annee"].value_counts())
print(df2022.shape)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/mspr_data_final")
df2022.to_sql("donnees_economie", engine, if_exists="append", index=False)