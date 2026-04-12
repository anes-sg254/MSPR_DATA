import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://postgres:mspr2026@localhost:5432/elections")

df = pd.read_sql("SELECT * FROM dataset_final", engine)


df["code_commune"] = df["code_commune"].astype(str)
df["commune"] = df["commune"].astype(str)

cols_num = [col for col in df.columns if col not in ["code_commune", "commune"]]
for col in cols_num:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df.to_csv("../data/donnes_clean/dataset_final_orange.csv", index=False)
print(df.dtypes)


df = pd.read_csv("../data/donnes_clean/dataset_final.csv")

df.to_excel("../data/donnes_clean/dataset_final.xlsx", index=False)

print("Conversion terminée : dataset_final_complet.xlsx")