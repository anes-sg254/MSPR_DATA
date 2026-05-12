import pandas as pd

df = pd.read_csv("../data/donnes_clean/securite_clean.csv", sep=";", low_memory=False)

print("Valeurs manquantes par colonne :")
print(df.isna().sum())

print("\nColonnes avec valeurs manquantes :")
print(df.isna().sum()[df.isna().sum() > 0])

print("\nNombre total de valeurs manquantes :")
print(df.isna().sum().sum())