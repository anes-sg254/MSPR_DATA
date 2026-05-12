import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

df = pd.read_csv(
    "../data/donnes_clean/dataset_final_31_33.csv",
    sep=";",
    encoding="latin-1",
    header=0
)


df = df.iloc[2:].reset_index(drop=True)


target_column = "parti_gagnant"

y = df[target_column]
X = df.drop(columns=[target_column])

X = X.drop(columns=["commune", "code_commune", "voix_parti", "id_parti"], errors="ignore")


for col in X.columns:
    X[col] = pd.to_numeric(X[col], errors="coerce")


valid_index = X.dropna().index
X = X.loc[valid_index]
y = y.loc[valid_index]


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)

print("Nombre de données d'entraînement :", len(X_train))
print("Nombre de données de test :", len(X_test))


model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)


model.fit(X_train, y_train)

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\nAccuracy :", accuracy)

print("\nPrecision / Recall / F1-score")
print(classification_report(y_test, y_pred))


exemples = pd.DataFrame({
    "Classe_observee": y_test.values,
    "Classe_estimee": y_pred
})

n = min(20, len(exemples))
print("\nExemples de résultats")
print(exemples.sample(n).reset_index(drop=True))