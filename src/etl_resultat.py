import pandas as pd
from sqlalchemy import create_engine

def nettoyer_resultat(path, id_election):
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
    df["nom"] = df["nom"].astype(str).str.strip()
    df["prenom"] = df["prenom"].astype(str).str.strip()

   
    df = df[df["code_commune"].str.startswith("31")]

    df = df[[
        "code_commune",
        "nom",
        "prenom",
        "voix"
    ]]

    df["voix"] = pd.to_numeric(df["voix"], errors="coerce")

    
    df = df.groupby(["code_commune", "nom", "prenom"], as_index=False)["voix"].sum()

    
    mapping_candidats = {
        ("ARTHAUD", "Nathalie"): 1,
        ("POUTOU", "Philippe"): 2,
        ("ROUSSEL", "Fabien"): 3,
        ("HIDALGO", "Anne"): 4,
        ("JADOT", "Yannick"): 5,
        ("MÉLENCHON", "Jean-Luc"): 6,
        ("MACRON", "Emmanuel"): 7,
        ("PÉCRESSE", "Valérie"): 8,
        ("LASSALLE", "Jean"): 9,
        ("DUPONT-AIGNAN", "Nicolas"): 10,
        ("LE PEN", "Marine"): 11,
        ("ZEMMOUR", "Éric"): 12
    }

    df["id_candidat"] = df.apply(
        lambda row: mapping_candidats.get((row["nom"], row["prenom"])),
        axis=1
    )

    
    df = df[df["id_candidat"].notna()].copy()
    df["id_candidat"] = df["id_candidat"].astype(int)

    
    df["id_election"] = id_election

    
    df = df[[
        "code_commune",
        "id_candidat",
        "id_election",
        "voix"
    ]]

    return df


df_resultat = nettoyer_resultat(
    "../data/donnes/candidats-results2022.csv",
    id_election=1
)

print(df_resultat.head())
print(df_resultat.shape)

df_resultat.to_csv("../data/donnes_clean/resultat_2022_clean.csv", index=False)

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/mspr_data_final")
df_resultat.to_sql("resultat", engine, if_exists="append", index=False)