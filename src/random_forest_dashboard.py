import json
import re
import unicodedata
from difflib import get_close_matches
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pydeck as pdk
import requests
import seaborn as sns
import streamlit as st

from random_forest import repair_commune_names, strip_accents, train_random_forest
from random_forest_2ndDash import build_analytic_dashboard


BASE_DIR = Path(__file__).resolve().parent.parent
ALLOWED_DEPARTMENTS = ("31", "33")
COMMUNE_CODE_CACHE_PATH = BASE_DIR / "data" / "donnes_clean" / "communes_code_cache.json"
COMMUNE_GEO_CACHE_PATH = BASE_DIR / "data" / "donnes_clean" / "communes_geo_by_code_cache.json"
GEO_API_URL = "https://geo.api.gouv.fr/communes"
LOCAL_REFERENCE_FILES = [
    BASE_DIR / "data" / "donnes_clean" / "demographie2_clean.csv",
    BASE_DIR / "data" / "donnes_clean" / "economie_clean.csv",
    BASE_DIR / "data" / "donnes_clean" / "dataset_final_31_33.csv",
]
PREDICTIVE_PARTY_COLORS = {
    "extreme_droite": [57, 231, 95, 190],
    "centre": [217, 70, 239, 190],
    "gauche": [79, 70, 229, 190],
    "droite": [224, 122, 95, 190],
}
COMMUNE_CODE_DISPLAY_FIXES = {
    "31076": "Bordes-de-Riviere",
    "31143": "Cier-de-Riviere",
    "31247": "Labarthe-Riviere",
    "31323": "Martres-de-Riviere",
    "31390": "Montrejeau",
    "31426": "Pointis-de-Riviere",
    "31475": "Saint-Clar-de-Riviere",
    "31585": "Villeneuve-de-Riviere",
}
DECK_TOOLTIP = {
    "html": (
        "<b>Commune:</b> {commune}<br/>"
        "<b>Code commune:</b> {resolved_code_commune}<br/>"
        "<b>Classe predite:</b> {classe_estimee}<br/>"
        "<b>Classe observee:</b> {classe_observee}<br/>"
        "<b>Poids carte:</b> {map_weight}<br/>"
        "<b>Confiance:</b> {confiance_modele}"
    ),
    "style": {
        "backgroundColor": "#0f172a",
        "color": "white",
    },
}


st.set_page_config(
    page_title="MSPR - Dashboard",
    layout="wide",
)

sns.set_theme(style="whitegrid")


@st.cache_data(show_spinner=False)
def load_results(test_size, random_state, n_estimators):
    return train_random_forest(
        test_size=test_size,
        random_state=random_state,
        n_estimators=n_estimators,
    )


def normalize_commune_name(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    normalized = normalized.encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def sanitize_commune_name(commune_name):
    raw = str(commune_name)

    try:
        repaired = raw.encode("latin-1").decode("utf-8")
        if repaired:
            raw = repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    raw = raw.replace("\x8a", "e").replace("\x82", "e")
    raw = raw.replace("\ufffd", "e")
    raw = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip(" -")


def build_search_candidates(commune_name):
    cleaned = sanitize_commune_name(commune_name)
    ascii_candidate = normalize_commune_name(cleaned).replace(" ", "-")
    plain_candidate = normalize_commune_name(cleaned)

    candidates = []
    for candidate in [cleaned, ascii_candidate, plain_candidate]:
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def finalize_commune_display(commune_name, code_commune=None):
    commune = strip_accents(sanitize_commune_name(commune_name))
    code_key = None if pd.isna(code_commune) else str(code_commune).strip().zfill(5)
    if code_key:
        commune = COMMUNE_CODE_DISPLAY_FIXES.get(code_key, commune)
    return re.sub(r"\s+", " ", commune).strip(" -")


def find_local_reference_match(commune_name, local_reference):
    normalized = normalize_commune_name(sanitize_commune_name(commune_name))
    direct_match = local_reference.get(normalized)
    if direct_match:
        return normalized, direct_match

    compact_normalized = normalized.replace(" ", "")
    for key, value in local_reference.items():
        if key.replace(" ", "") == compact_normalized:
            return key, value

    compact_reference = {key.replace(" ", ""): (key, value) for key, value in local_reference.items()}
    close_matches = get_close_matches(
        compact_normalized,
        list(compact_reference.keys()),
        n=1,
        cutoff=0.8,
    )
    if close_matches:
        matched_key, matched_value = compact_reference[close_matches[0]]
        return matched_key, matched_value

    return normalized, None


def load_json_cache(path):
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_json_cache(path, payload):
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@st.cache_data(show_spinner=False)
def load_local_commune_reference():
    frames = []
    for file_path in LOCAL_REFERENCE_FILES:
        if not file_path.exists():
            continue

        df = pd.read_csv(file_path)
        required_columns = {"code_commune", "commune"}
        if not required_columns.issubset(df.columns):
            continue

        subset = df[["code_commune", "commune"]].copy()
        subset["code_commune"] = subset["code_commune"].astype(str).str.zfill(5)
        subset["commune"] = subset.apply(
            lambda row: finalize_commune_display(row["commune"], row["code_commune"]),
            axis=1,
        )
        frames.append(subset)

    if not frames:
        return {}

    reference_df = pd.concat(frames, ignore_index=True).drop_duplicates()
    reference_df["normalized_commune"] = reference_df["commune"].map(normalize_commune_name)
    reference_df["code_departement"] = reference_df["code_commune"].str[:2]
    reference_df = reference_df.drop_duplicates(subset=["normalized_commune", "code_commune"])

    return {
        row["normalized_commune"]: {
            "resolved_code_commune": row["code_commune"],
            "resolved_code_departement": row["code_departement"],
            "resolution_source": "local_reference",
            "resolved_commune": strip_accents(row["commune"]),
        }
        for _, row in reference_df.iterrows()
    }


def backfill_resolution_from_reference(predictions_df):
    if predictions_df.empty or "commune" not in predictions_df.columns:
        return predictions_df

    local_reference = load_local_commune_reference()
    enriched = predictions_df.copy()

    def fill_row(row):
        commune_value = row.get("commune")
        code_value = row.get("resolved_code_commune")
        normalized, match = find_local_reference_match(
            finalize_commune_display(commune_value, code_value),
            local_reference,
        )
        if not match:
            return row

        row["commune"] = match.get("resolved_commune", row.get("commune"))
        if pd.isna(row.get("resolved_code_commune")) or not str(
            row.get("resolved_code_commune")
        ).strip():
            row["resolved_code_commune"] = match.get("resolved_code_commune")
        if pd.isna(row.get("resolved_code_departement")) or not str(
            row.get("resolved_code_departement")
        ).strip():
            row["resolved_code_departement"] = match.get("resolved_code_departement")
        if pd.isna(row.get("resolution_source")) or not str(row.get("resolution_source")).strip():
            row["resolution_source"] = "local_reference"
        return row

    return enriched.apply(fill_row, axis=1)


def resolve_commune_code(commune_name, session, code_cache, local_reference):
    normalized_name, reference_match = find_local_reference_match(
        commune_name, local_reference
    )

    if reference_match:
        code_cache[normalized_name] = reference_match
        return code_cache[normalized_name]

    cached_resolution = code_cache.get(normalized_name)
    if cached_resolution:
        return cached_resolution

    exact_matches = {}
    for department_code in ALLOWED_DEPARTMENTS:
        for candidate in build_search_candidates(commune_name):
            response = session.get(
                GEO_API_URL,
                params={
                    "nom": candidate,
                    "fields": "nom,code,departement",
                    "boost": "population",
                    "codeDepartement": department_code,
                },
                timeout=20,
            )
            response.raise_for_status()

            payload = response.json()
            for item in payload:
                item_name = normalize_commune_name(item.get("nom", ""))
                item_code = item.get("code")
                item_department = (item.get("departement") or {}).get("code")

                if (
                    item_name == normalized_name
                    and item_code
                    and item_department in ALLOWED_DEPARTMENTS
                ):
                    exact_matches[item_code] = {
                        "resolved_code_commune": item_code,
                        "resolved_code_departement": item_department,
                        "resolution_source": f"geo_api_name_{item_department}",
                    }

    if len(exact_matches) == 1:
        resolved = next(iter(exact_matches.values()))
        code_cache[normalized_name] = resolved
        return resolved

    code_cache[normalized_name] = None
    return None


def fetch_commune_geo_by_code(code_commune, session, geo_cache):
    code_commune = str(code_commune).zfill(5)
    if code_commune in geo_cache:
        return geo_cache[code_commune]

    response = session.get(
        GEO_API_URL,
        params={
            "code": code_commune,
            "fields": "nom,code,centre,departement",
        },
        timeout=20,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload:
        geo_cache[code_commune] = None
        return None

    item = payload[0]
    coordinates = (item.get("centre") or {}).get("coordinates", [])
    department_code = (item.get("departement") or {}).get("code")

    if len(coordinates) != 2 or department_code not in ALLOWED_DEPARTMENTS:
        geo_cache[code_commune] = None
        return None

    geo_cache[code_commune] = {
        "commune_api": item.get("nom"),
        "resolved_code_commune": item.get("code"),
        "code_departement": department_code,
        "nom_departement": (item.get("departement") or {}).get("nom"),
        "longitude": coordinates[0],
        "latitude": coordinates[1],
    }
    return geo_cache[code_commune]


@st.cache_data(show_spinner=False)
def enrich_predictions_with_geo(prediction_samples):
    code_cache = load_json_cache(COMMUNE_CODE_CACHE_PATH)
    geo_cache = load_json_cache(COMMUNE_GEO_CACHE_PATH)
    local_reference = load_local_commune_reference()
    session = requests.Session()

    rows = []
    code_cache_updated = False
    geo_cache_updated = False
    network_error = False

    metadata_columns = ["commune"]
    if "code_commune" in prediction_samples.columns:
        metadata_columns.append("code_commune")

    unique_rows = prediction_samples[metadata_columns].drop_duplicates()

    for _, row in unique_rows.iterrows():
        commune_name = row["commune"]
        input_code = row.get("code_commune")
        normalized_name = normalize_commune_name(sanitize_commune_name(commune_name))
        reference_match = local_reference.get(normalized_name)
        display_commune = (
            reference_match.get("resolved_commune")
            if reference_match and reference_match.get("resolved_commune")
            else finalize_commune_display(commune_name)
        )

        if pd.notna(input_code) and str(input_code).strip():
            resolved_code = {
                "resolved_code_commune": str(input_code).strip().zfill(5),
                "resolved_code_departement": str(input_code).strip().zfill(5)[:2],
                "resolution_source": "dataset",
            }
        else:
            if normalized_name not in code_cache:
                code_cache_updated = True
            try:
                resolved_code = resolve_commune_code(
                    commune_name,
                    session,
                    code_cache,
                    local_reference,
                )
            except requests.RequestException:
                network_error = True
                resolved_code = None

        if not resolved_code:
            rows.append(
                {
                    "commune_source": commune_name,
                    "commune_display": display_commune,
                    "resolved_code_commune": None,
                    "resolved_code_departement": None,
                    "resolution_source": "unresolved",
                    "latitude": None,
                    "longitude": None,
                    "nom_departement": None,
                }
            )
            continue

        resolved_code_commune = resolved_code["resolved_code_commune"]
        if resolved_code_commune not in geo_cache:
            geo_cache_updated = True

        try:
            geo_row = fetch_commune_geo_by_code(resolved_code_commune, session, geo_cache)
        except requests.RequestException:
            network_error = True
            geo_row = None

        if not geo_row:
            rows.append(
                {
                    "commune_source": commune_name,
                    "commune_display": display_commune,
                    "resolved_code_commune": resolved_code_commune,
                    "resolved_code_departement": resolved_code["resolved_code_departement"],
                    "resolution_source": resolved_code["resolution_source"],
                    "latitude": None,
                    "longitude": None,
                    "nom_departement": None,
                }
            )
            continue

        rows.append(
            {
                "commune_source": commune_name,
                "commune_display": display_commune,
                "resolved_code_commune": geo_row["resolved_code_commune"],
                "resolved_code_departement": geo_row["code_departement"],
                "resolution_source": resolved_code["resolution_source"],
                "latitude": geo_row["latitude"],
                "longitude": geo_row["longitude"],
                "nom_departement": geo_row["nom_departement"],
            }
        )

    if code_cache_updated:
        save_json_cache(COMMUNE_CODE_CACHE_PATH, code_cache)
    if geo_cache_updated:
        save_json_cache(COMMUNE_GEO_CACHE_PATH, geo_cache)

    enrichment_df = pd.DataFrame(rows).drop_duplicates(subset=["commune_source"])
    if enrichment_df.empty:
        enrichment_df = pd.DataFrame(
            columns=[
                "commune_source",
                "commune_display",
                "resolved_code_commune",
                "resolved_code_departement",
                "resolution_source",
                "latitude",
                "longitude",
                "nom_departement",
            ]
        )

    merged = prediction_samples.merge(
        enrichment_df,
        left_on="commune",
        right_on="commune_source",
        how="left",
    )
    if "commune_display" in merged.columns:
        merged["commune"] = merged["commune_display"].fillna(
            merged.apply(
                lambda row: finalize_commune_display(
                    row["commune"], row.get("resolved_code_commune")
                ),
                axis=1,
            )
        )
    if "resolved_code_commune" in merged.columns:
        merged["commune"] = merged.apply(
            lambda row: finalize_commune_display(
                row["commune"], row.get("resolved_code_commune")
            ),
            axis=1,
        )
    merged = merged.drop(columns=["commune_source", "commune_display"], errors="ignore")

    return {"data": merged, "network_error": network_error}


def plot_confusion_matrix(confusion_matrix_data, labels):
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(
        confusion_matrix_data,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
    )
    ax.set_title("Matrice de confusion")
    ax.set_xlabel("Classe predite")
    ax.set_ylabel("Classe observee")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    fig.tight_layout()
    return fig


def plot_feature_importance(feature_importance, top_n):
    top_features = (
        feature_importance.head(top_n)
        .sort_values("importance", ascending=True)
        .reset_index(drop=True)
    )

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top_features["feature"], top_features["importance"], color="#2E8B57")
    ax.set_title(f"Top {top_n} des variables les plus importantes")
    ax.set_xlabel("Importance")
    ax.set_ylabel("Variable")
    fig.tight_layout()
    return fig


def plot_prediction_distribution(prediction_samples):
    distribution = (
        prediction_samples[["classe_observee", "classe_estimee"]]
        .melt(var_name="type", value_name="classe")
        .groupby(["type", "classe"])
        .size()
        .reset_index(name="effectif")
    )
    distribution["type"] = distribution["type"].map(
        {
            "classe_observee": "Observee",
            "classe_estimee": "Predite",
        }
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=distribution,
        x="classe",
        y="effectif",
        hue="type",
        palette=["#4C72B0", "#55A868"],
        ax=ax,
    )
    ax.set_title("Repartition des classes observees vs predites")
    ax.set_xlabel("Classe")
    ax.set_ylabel("Nombre de communes")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    return fig


def build_party_color_legend():
    legend_items = []
    for party, color in PREDICTIVE_PARTY_COLORS.items():
        rgb = f"rgb({color[0]}, {color[1]}, {color[2]})"
        legend_items.append(
            (
                "<span style='display:inline-flex;align-items:center;margin-right:18px;'>"
                f"<span style='width:12px;height:12px;border-radius:999px;"
                f"background:{rgb};display:inline-block;margin-right:8px;'></span>"
                f"<span>{party}</span>"
                "</span>"
            )
        )
    return "".join(legend_items)


def build_geographic_map(geo_predictions, selected_class):
    geo_predictions = geo_predictions.copy()
    geo_predictions["confiance_modele"] = geo_predictions["confiance_modele"].round(4)
    if selected_class == "Tous":
        geo_predictions["map_weight"] = geo_predictions["confiance_modele"]
        scatter_predictions = geo_predictions.copy()
    else:
        geo_predictions["map_weight"] = geo_predictions[selected_class].round(4)
        scatter_predictions = geo_predictions[
            geo_predictions["classe_estimee"] == selected_class
        ].copy()
    geo_predictions["party_color"] = geo_predictions["classe_estimee"].map(
        lambda party: PREDICTIVE_PARTY_COLORS.get(party, [15, 23, 42, 190])
    )
    scatter_predictions["party_color"] = scatter_predictions["classe_estimee"].map(
        lambda party: PREDICTIVE_PARTY_COLORS.get(party, [15, 23, 42, 190])
    )

    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=geo_predictions,
        get_position="[longitude, latitude]",
        get_weight="map_weight",
        aggregation="SUM",
        radiusPixels=60,
    )
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=scatter_predictions,
        get_position="[longitude, latitude]",
        get_radius=4500,
        get_fill_color="party_color",
        pickable=True,
        stroked=True,
        get_line_color=[30, 41, 59, 180],
        line_width_min_pixels=1,
    )

    view_state = pdk.ViewState(
        latitude=float(geo_predictions["latitude"].mean()),
        longitude=float(geo_predictions["longitude"].mean()),
        zoom=7,
        pitch=0,
    )

    return pdk.Deck(
        layers=[heatmap_layer, scatter_layer],
        initial_view_state=view_state,
        tooltip=DECK_TOOLTIP,
    )


def build_predictive_dashboard():
    st.title("Dashboard de sortie du modele Random Forest")
    st.write(
        "Ce dashboard permet de visualiser la performance du modele, "
        "les predictions et l'importance des variables explicatives."
    )

    with st.sidebar:
        st.header("Parametres predictifs")
        test_size = st.slider(
            "Part du jeu de test",
            0.10,
            0.50,
            0.30,
            0.05,
            key="predictive_test_size",
        )
        n_estimators = st.slider(
            "Nombre d'arbres",
            50,
            500,
            100,
            50,
            key="predictive_n_estimators",
        )
        random_state = st.number_input(
            "Random state",
            min_value=0,
            value=42,
            step=1,
            key="predictive_random_state",
        )
        top_n_features = st.slider(
            "Variables a afficher",
            5,
            20,
            10,
            1,
            key="predictive_top_n_features",
        )

    with st.spinner("Entrainement du modele et preparation des visualisations..."):
        results = load_results(test_size, int(random_state), int(n_estimators))

    with st.sidebar:
        selected_predicted_party = st.selectbox(
            "Parti predit",
            options=["Tous"] + results["class_labels"],
            index=0,
            key="predictive_selected_party",
        )

    metrics = results["metrics"]
    prediction_samples = results["prediction_samples"]
    feature_importance = results["feature_importance"]
    predictive_rows = pd.concat(
        [
            prediction_samples.reset_index(drop=True),
            results["probabilities"].reset_index(drop=True),
        ],
        axis=1,
    )
    if selected_predicted_party != "Tous":
        predictive_rows = predictive_rows[
            predictive_rows["classe_estimee"] == selected_predicted_party
        ].copy()

    commune_probability_matrix = predictive_rows[
        ["commune", "confiance_modele"] + results["class_labels"]
    ].copy()
    commune_probability_matrix["commune"] = repair_commune_names(
        commune_probability_matrix["commune"]
    ).map(strip_accents)

    correct_predictions = int(prediction_samples["prediction_correcte"].sum())
    total_predictions = len(prediction_samples)
    accuracy_pct = metrics["accuracy"] * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accuracy", f"{accuracy_pct:.2f}%")
    col2.metric("Jeu d'entrainement", len(results["X_train"]))
    col3.metric("Jeu de test", len(results["X_test"]))
    col4.metric("Predictions correctes", f"{correct_predictions}/{total_predictions}")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Matrice de confusion")
        st.pyplot(
            plot_confusion_matrix(
                metrics["confusion_matrix"],
                results["class_labels"],
            ),
            clear_figure=True,
        )

    with chart_col2:
        st.subheader("Variables les plus influentes")
        st.pyplot(
            plot_feature_importance(feature_importance, top_n_features),
            clear_figure=True,
        )

    st.subheader("Repartition des predictions")
    if predictive_rows.empty:
        st.info("Aucune prediction ne correspond au parti selectionne.")
    else:
        st.pyplot(
            plot_prediction_distribution(
                predictive_rows[
                    ["classe_observee", "classe_estimee", "confiance_modele", "prediction_correcte"]
                ]
            ),
            clear_figure=True,
        )

    st.subheader("Carte geographique des predictions")
    geographic_predictions = predictive_rows.copy()

    with st.spinner("Resolution des codes communes et construction de la carte..."):
        geo_enrichment = enrich_predictions_with_geo(geographic_predictions)
        geographic_predictions = backfill_resolution_from_reference(geo_enrichment["data"])

    map_col1, map_col2 = st.columns([2, 1])

    with map_col2:
        selected_class = st.selectbox(
            "Classe a representer sur la heatmap",
            options=["Tous"] + results["class_labels"],
            key="predictive_selected_class",
        )
        map_mode = st.radio(
            "Filtre de lignes",
            options=["Toutes", "Correctes", "Erreurs"],
            horizontal=True,
            key="predictive_map_mode",
        )

    if map_mode == "Correctes":
        geographic_predictions = geographic_predictions[
            geographic_predictions["prediction_correcte"]
        ]
    elif map_mode == "Erreurs":
        geographic_predictions = geographic_predictions[
            ~geographic_predictions["prediction_correcte"]
        ]

    valid_geo_predictions = geographic_predictions.dropna(
        subset=["latitude", "longitude", "resolved_code_commune"]
    ).copy()

    matched_communes = valid_geo_predictions["commune"].nunique()
    total_communes = predictive_rows["commune"].nunique()
    unresolved_communes = total_communes - matched_communes

    if predictive_rows.empty:
        with map_col1:
            st.info("Aucune prediction a cartographier pour le parti selectionne.")
    elif valid_geo_predictions.empty:
        with map_col1:
            st.warning(
                "Aucune commune n'a pu etre resolue avec un code commune fiable pour le filtre selectionne."
            )
    else:
        with map_col1:
            st.pydeck_chart(
                build_geographic_map(valid_geo_predictions, selected_class),
                use_container_width=True,
            )
            st.markdown(
                (
                    "<div style='margin-top:8px;font-size:0.95rem;color:#111827;'>"
                    "<b>Couleurs des partis predits :</b> "
                    f"{build_party_color_legend()}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    st.write(
        f"Communes cartographiees: {matched_communes}/{total_communes}. "
        f"Communes exclues faute de code fiable: {unresolved_communes}."
    )

    st.subheader("Communes couvertes sur la carte")
    resolution_overview = geographic_predictions[
        [
            "commune",
            "resolved_code_commune",
            "resolved_code_departement",
            "classe_estimee",
            "confiance_modele",
        ]
    ].drop_duplicates()
    resolution_overview = resolution_overview.rename(
        columns={
            "commune": "Commune",
            "resolved_code_commune": "Code commune",
            "resolved_code_departement": "Departement",
            "classe_estimee": "Parti predit",
            "confiance_modele": "Niveau de confiance",
        }
    )
    resolution_overview["Niveau de confiance"] = (
        resolution_overview["Niveau de confiance"] * 100
    ).round(1)
    resolution_overview = resolution_overview.fillna(
        {
            "Code commune": "Non renseigne",
            "Departement": "Non renseigne",
            "Parti predit": "Non renseigne",
            "Niveau de confiance": 0,
        }
    )
    st.dataframe(
        resolution_overview.sort_values(["Departement", "Commune"]),
        use_container_width=True,
    )

    st.subheader("Heatmap par commune")
    heatmap_col1, heatmap_col2 = st.columns([2, 1])

    with heatmap_col2:
        sort_mode = st.selectbox(
            "Trier les communes par",
            options=[
                "Confiance du modele",
                "Ordre alphabetique",
            ],
            key="predictive_sort_mode",
        )
        if commune_probability_matrix.empty:
            commune_limit = 0
        else:
            max_communes = min(100, len(commune_probability_matrix))
            min_communes = min(10, max_communes)
            default_communes = min(30, max_communes)
            commune_limit = st.slider(
                "Nombre de communes affichees",
                min_value=min_communes,
                max_value=max_communes,
                value=default_communes,
                step=5 if max_communes >= 10 else 1,
                key="predictive_commune_limit",
            )

    if sort_mode == "Ordre alphabetique":
        commune_probability_matrix = commune_probability_matrix.sort_values("commune")
    else:
        commune_probability_matrix = commune_probability_matrix.sort_values(
            "confiance_modele",
            ascending=False,
        )

    with heatmap_col1:
        if commune_probability_matrix.empty:
            st.info("Aucune commune a afficher pour le parti selectionne.")
        else:
            heatmap_data = (
                commune_probability_matrix.head(commune_limit)
                .drop(columns=["confiance_modele"], errors="ignore")
                .set_index("commune")
            )
            height = max(6, min(20, len(heatmap_data) * 0.35))
            fig, ax = plt.subplots(figsize=(12, height))
            sns.heatmap(
                heatmap_data,
                cmap="YlOrRd",
                vmin=0,
                vmax=1,
                linewidths=0.2,
                linecolor="white",
                cbar_kws={"label": "Probabilite predite"},
                ax=ax,
            )
            ax.set_title("Heatmap des probabilites predites par commune")
            ax.set_xlabel("Classe politique")
            ax.set_ylabel("Commune")
            plt.xticks(rotation=45, ha="right")
            plt.yticks(rotation=0)
            fig.tight_layout()
            st.pyplot(fig, clear_figure=True)

    st.subheader("Lecture metier par parti")
    party_summary = (
        predictive_rows.groupby("classe_estimee")
        .agg(
            nb_communes=("commune", "count"),
            confiance_moyenne=("confiance_modele", "mean"),
            predictions_correctes=("prediction_correcte", "sum"),
        )
        .reset_index()
        .rename(columns={"classe_estimee": "Parti predit"})
    )
    party_summary["Part des communes"] = (
        party_summary["nb_communes"] / max(len(predictive_rows), 1) * 100
    ).round(1)
    party_summary["Taux de prediction juste"] = (
        party_summary["predictions_correctes"] / party_summary["nb_communes"].clip(lower=1) * 100
    ).round(1)
    party_summary["Confiance moyenne"] = (party_summary["confiance_moyenne"] * 100).round(1)
    party_summary = party_summary.rename(
        columns={
            "nb_communes": "Nombre de communes",
            "predictions_correctes": "Predictions justes",
        }
    )[
        [
            "Parti predit",
            "Nombre de communes",
            "Part des communes",
            "Confiance moyenne",
            "Predictions justes",
            "Taux de prediction juste",
        ]
    ].sort_values("Nombre de communes", ascending=False)
    st.dataframe(party_summary, use_container_width=True)

    st.subheader("Communes et orientation predite")
    display_mode = st.radio(
        "Filtrer les predictions",
        options=["Toutes", "Correctes", "Erreurs"],
        horizontal=True,
        key="predictive_display_mode",
    )

    filtered_predictions = geographic_predictions.copy()
    if display_mode == "Correctes":
        filtered_predictions = filtered_predictions[
            filtered_predictions["prediction_correcte"]
        ]
    elif display_mode == "Erreurs":
        filtered_predictions = filtered_predictions[
            ~filtered_predictions["prediction_correcte"]
        ]

    if filtered_predictions.empty:
        st.info("Aucune ligne ne correspond au filtre selectionne.")
    else:
        business_predictions = filtered_predictions.copy()
        business_predictions["confiance_modele"] = (
            business_predictions["confiance_modele"] * 100
        ).round(1)
        business_predictions["prediction_correcte"] = business_predictions[
            "prediction_correcte"
        ].map({True: "Oui", False: "Non"})
        business_columns = [
            col
            for col in [
                "commune",
                "resolved_code_departement",
                "resolved_code_commune",
                "classe_observee",
                "classe_estimee",
                "confiance_modele",
                "prediction_correcte",
            ]
            if col in business_predictions.columns
        ]
        business_predictions = business_predictions[business_columns].rename(
            columns={
                "commune": "Commune",
                "resolved_code_departement": "Departement",
                "resolved_code_commune": "Code commune",
                "classe_observee": "Parti observe",
                "classe_estimee": "Parti predit",
                "confiance_modele": "Niveau de confiance",
                "prediction_correcte": "Prediction juste",
            }
        )
        business_predictions = business_predictions.fillna(
            {
                "Commune": "Non renseignee",
                "Departement": "Non renseigne",
                "Code commune": "Non renseigne",
                "Parti observe": "Non renseigne",
                "Parti predit": "Non renseigne",
                "Niveau de confiance": 0,
                "Prediction juste": "Non",
            }
        )
        st.dataframe(
            business_predictions.sort_values("Niveau de confiance", ascending=False),
            use_container_width=True,
        )


def build_dashboard():
    st.title("Dashboard MSPR")

    analytic_tab, predictive_tab = st.tabs(
        [
            "Visualisations analytiques et decisionnelles",
            "Visualisations predictives",
        ]
    )

    with analytic_tab:
        build_analytic_dashboard()

    with predictive_tab:
        build_predictive_dashboard()


if __name__ == "__main__":
    build_dashboard()
