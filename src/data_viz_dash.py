from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from random_forest import read_csv_flexible, repair_commune_names, strip_accents


BASE_DIR = Path(__file__).resolve().parent.parent
COLOR_MAP = {
    "extreme_droite": "#39E75F",
    "centre": "#D946EF",
    "gauche": "#4F46E5",
    "droite": "#E07A5F",
}
PARTI_LABELS = {
    "extreme_droite": "Extreme droite",
    "gauche": "Gauche",
    "centre": "Centre",
    "droite": "Droite",
}
SECURITY_COLS = [
    "pct_violences_hors_famille",
    "pct_violences_intrafamiliales",
    "pct_degradations_volontaires",
    "pct_usage_stupefiants",
    "pct_cambriolages_logement",
    "pct_vols_vehicule",
]


def inject_analytic_styles():
    st.markdown(
        """
<style>
.block-container {
    padding-top: 1.2rem;
}
.info-box {
    background-color: #f8fafc;
    border-left: 5px solid #2563eb;
    padding: 12px 16px;
    border-radius: 10px;
    margin-bottom: 16px;
    color: #334155;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def find_default_csv():
    candidates = [
        BASE_DIR / "data" / "donnes_clean" / "dataset_final_31_33.csv",
        BASE_DIR / "dataset_final_31_33.csv",
        Path("dataset_final_31_33.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


@st.cache_data(show_spinner=False)
def load_analytic_data():
    source = find_default_csv()
    if source is None:
        raise FileNotFoundError("Le fichier dataset_final_31_33.csv est introuvable.")

    df = read_csv_flexible(source)

    df.columns = df.columns.astype(str).str.strip()

    text_columns = {"parti_gagnant", "commune", "departement", "code_commune"}
    for col in df.columns:
        if col not in text_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "code_commune" in df.columns:
        df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)

    df = df.dropna(subset=["parti_gagnant", "commune"]).copy()
    df["commune"] = repair_commune_names(df["commune"])
    df["commune"] = df["commune"].map(strip_accents)

    if "population" in df.columns:
        df["population"] = df["population"].fillna(df["population"].median()).clip(lower=1)

    return df


def available_cols(df, cols):
    return [col for col in cols if col in df.columns]


def format_parti(value):
    return PARTI_LABELS.get(value, value)


def compute_zoom_range(series, lower_quantile=0.03, upper_quantile=0.97, padding_ratio=0.08):
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None

    lower = float(values.quantile(lower_quantile))
    upper = float(values.quantile(upper_quantile))

    if lower == upper:
        spread = max(abs(lower) * padding_ratio, 1.0)
        return [lower - spread, upper + spread]

    spread = upper - lower
    padding = spread * padding_ratio
    minimum = float(values.min())
    maximum = float(values.max())
    return [max(minimum, lower - padding), min(maximum, upper + padding)]


def add_question_box(text):
    st.markdown(
        f"""
        <div class="info-box">
            <b>Question decisionnelle :</b> {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_security_abstention_figure(filtered_df):
    pressure_df = filtered_df.dropna(subset=SECURITY_COLS + ["taux_abstention"]).copy()
    pressure_df["indice_securite"] = pressure_df[SECURITY_COLS].mean(axis=1) * 100
    pressure_df = pressure_df[pressure_df["indice_securite"] > 0].copy()

    fig = px.scatter(
        pressure_df,
        x="indice_securite",
        y="taux_abstention",
        color="parti_gagnant",
        hover_name="commune",
        hover_data=["code_commune"] if "code_commune" in pressure_df.columns else None,
        color_discrete_map=COLOR_MAP,
        opacity=0.78,
        title="Nuage de points : securite et abstention electorale",
        labels={
            "indice_securite": "Indice de pression securitaire",
            "taux_abstention": "Taux d'abstention (%)",
            "parti_gagnant": "Parti gagnant",
        },
    )
    fig.update_traces(
        marker=dict(size=10, line=dict(width=1, color="rgba(80,80,80,0.45)"))
    )

    if len(pressure_df) > 2 and pressure_df["indice_securite"].nunique() > 1:
        z = np.polyfit(pressure_df["indice_securite"], pressure_df["taux_abstention"], 1)
        p = np.poly1d(z)
        x_line = np.linspace(
            pressure_df["indice_securite"].min(),
            pressure_df["indice_securite"].max(),
            100,
        )
        fig.add_scatter(
            x=x_line,
            y=p(x_line),
            mode="lines",
            line=dict(color="black", dash="dot", width=2),
            name="Tendance",
        )

    fig.update_layout(
        height=620,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Indice de pression securitaire",
        yaxis_title="Taux d'abstention (%)",
        legend_title="parti_gagnant",
        legend=dict(font=dict(color="black"), title=dict(font=dict(color="black"))),
    )
    fig.update_xaxes(
        range=[0, 80],
        dtick=20,
        showgrid=True,
        gridcolor="rgba(180,180,180,0.35)",
        zeroline=False,
    )
    fig.update_yaxes(
        range=[0, 60],
        dtick=20,
        showgrid=True,
        gridcolor="rgba(180,180,180,0.35)",
        zeroline=False,
    )
    return pressure_df, fig


def build_analytic_dashboard():
    inject_analytic_styles()
    st.title("Visualisations analytiques et decisionnelles")

    try:
        df = load_analytic_data()
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    with st.sidebar:
        st.header("Filtres analytiques")
        partis = ["Tous"] + sorted(df["parti_gagnant"].dropna().unique().tolist())
        selected_parti = st.selectbox(
            "Parti gagnant",
            partis,
            key="analytic_selected_parti",
        )
        communes = ["Toutes"] + sorted(df["commune"].dropna().unique().tolist())
        selected_commune = st.selectbox(
            "Commune",
            communes,
            key="analytic_selected_commune",
        )

    filtered_df = df.copy()
    if selected_parti != "Tous":
        filtered_df = filtered_df[filtered_df["parti_gagnant"] == selected_parti]
    if selected_commune != "Toutes":
        filtered_df = filtered_df[filtered_df["commune"] == selected_commune]

    if filtered_df.empty:
        st.warning("Aucune donnee disponible avec les filtres selectionnes.")
        return

    tab1, tab2, tab3 = st.tabs(
        [
            "Profil socio-demographique",
            "Securite et abstention",
            "Economie et attractivite",
        ]
    )

    with tab1:
        st.subheader("Profil socio-demographique")
        add_question_box("Ou cibler les politiques jeunesse et les politiques sociales ?")

        required_demo = ["part_jeunes", "part_seniors", "population", "parti_gagnant", "commune"]
        missing_demo = [col for col in required_demo if col not in filtered_df.columns]

        if missing_demo:
            st.warning(f"Colonnes manquantes pour le scatter demographique : {missing_demo}")
        else:
            scatter_demo = filtered_df.dropna(subset=["part_jeunes", "part_seniors"]).copy()
            scatter_demo["taille_point"] = (
                scatter_demo["population"]
                .fillna(scatter_demo["population"].median())
                .clip(lower=1)
            )
            x_range_demo = compute_zoom_range(scatter_demo["part_jeunes"], 0.04, 0.98, 0.1)
            y_range_demo = compute_zoom_range(scatter_demo["part_seniors"], 0.03, 0.97, 0.12)

            fig_demo_scatter = px.scatter(
                scatter_demo,
                x="part_jeunes",
                y="part_seniors",
                size="taille_point",
                size_max=44,
                color="parti_gagnant",
                hover_name="commune",
                color_discrete_map=COLOR_MAP,
                title="Jeunes vs seniors par commune",
                labels={
                    "part_jeunes": "% jeunes",
                    "part_seniors": "% seniors",
                    "parti_gagnant": "Parti gagnant",
                },
                range_x=x_range_demo,
                range_y=y_range_demo,
            )
            fig_demo_scatter.update_traces(
                marker=dict(line=dict(width=0.8, color="rgba(255,255,255,0.65)"), opacity=0.88)
            )
            fig_demo_scatter.add_vline(
                x=scatter_demo["part_jeunes"].mean(),
                line_dash="dash",
                line_color="gray",
                annotation_text="Moy. jeunes",
            )
            fig_demo_scatter.add_hline(
                y=scatter_demo["part_seniors"].mean(),
                line_dash="dash",
                line_color="gray",
                annotation_text="Moy. seniors",
            )
            fig_demo_scatter.update_layout(height=650)
            st.plotly_chart(fig_demo_scatter, use_container_width=True)

        st.markdown("### Distribution de l'indice de jeunesse par parti")
        if "indice_jeunesse" in filtered_df.columns:
            box_df = filtered_df.dropna(subset=["indice_jeunesse"]).copy()
            box_df["parti_affiche"] = box_df["parti_gagnant"].apply(format_parti)

            fig_box = px.box(
                box_df,
                x="parti_affiche",
                y="indice_jeunesse",
                color="parti_gagnant",
                points="outliers",
                color_discrete_map=COLOR_MAP,
                title="Distribution de l'indice de jeunesse par parti",
                labels={
                    "parti_affiche": "Parti gagnant",
                    "indice_jeunesse": "Indice de jeunesse",
                },
            )
            fig_box.add_hline(
                y=1,
                line_dash="dash",
                line_color="gray",
                annotation_text="Equilibre jeunes / seniors",
            )
            fig_box.update_layout(showlegend=False, height=520)
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.warning("Colonne indice_jeunesse introuvable.")

    with tab2:
        st.subheader("Securite et abstention")
        add_question_box(
            "Existe-t-il un lien entre pression securitaire et abstention electorale ?"
        )

        required_security = SECURITY_COLS + ["taux_abstention", "commune", "parti_gagnant"]
        missing_security = [col for col in required_security if col not in filtered_df.columns]
        if missing_security:
            st.warning(
                f"Colonnes manquantes pour le nuage de points securite/abstention : {missing_security}"
            )
        else:
            pressure_df, fig = build_security_abstention_figure(filtered_df)
            if pressure_df.empty:
                st.warning("Aucune ligne exploitable apres nettoyage pour ce nuage de points.")
            else:
                st.plotly_chart(fig, use_container_width=True)
                st.info(
                    "Chaque point represente une commune. Plus on va a droite, plus la pression "
                    "securitaire estimee est forte. Plus on monte, plus l'abstention est elevee."
                )

        st.markdown("### Comparatif des indicateurs de criminalite par parti")
        selected_crimes = available_cols(
            filtered_df,
            [
                "pct_cambriolages_logement",
                "pct_usage_stupefiants",
                "pct_violences_intrafamiliales",
                "pct_degradations_volontaires",
                "pct_vols_vehicule",
            ],
        )
        if selected_crimes:
            crime_means = filtered_df.groupby("parti_gagnant")[selected_crimes].mean().reset_index()
            crime_long = crime_means.melt(
                id_vars="parti_gagnant",
                value_vars=selected_crimes,
                var_name="indicateur",
                value_name="valeur_moyenne",
            )
            fig_crime = px.bar(
                crime_long,
                x="indicateur",
                y="valeur_moyenne",
                color="parti_gagnant",
                barmode="group",
                color_discrete_map=COLOR_MAP,
                title="Comparatif criminalite par parti",
            )
            fig_crime.update_layout(
                xaxis_title="Indicateur de criminalite",
                yaxis_title="Valeur moyenne",
                xaxis_tickangle=-25,
                height=560,
            )
            st.plotly_chart(fig_crime, use_container_width=True)

        st.markdown("### Top 10 communes a risque - score composite")
        crime_cols = available_cols(
            filtered_df,
            [
                "pct_vols_avec_armes",
                "pct_vols_violents_sans_arme",
                "pct_vols_sans_violence_personnes",
                "pct_cambriolages_logement",
                "pct_vols_vehicule",
                "pct_vols_dans_vehicules",
                "pct_vols_accessoires_vehicules",
                "pct_degradations_volontaires",
                "pct_usage_stupefiants",
                "pct_violences_intrafamiliales",
                "pct_violences_hors_famille",
                "pct_violences_sexuelles",
            ],
        )
        if crime_cols:
            risk_df = filtered_df[["commune", "parti_gagnant"] + crime_cols].copy()
            risk_df["score_criminalite"] = risk_df[crime_cols].sum(axis=1)
            top_risk = (
                risk_df.sort_values("score_criminalite", ascending=False)
                .head(10)
                .sort_values("score_criminalite", ascending=True)
            )

            fig_risk = px.bar(
                top_risk,
                x="score_criminalite",
                y="commune",
                orientation="h",
                color="parti_gagnant",
                color_discrete_map=COLOR_MAP,
                text=top_risk["score_criminalite"].round(2),
                title="Classement des communes les plus exposees",
            )
            fig_risk.update_layout(
                xaxis_title="Score composite de criminalite",
                yaxis_title="Commune",
                showlegend=True,
                height=560,
            )
            st.plotly_chart(fig_risk, use_container_width=True)

    with tab3:
        st.subheader("Economie et attractivite")
        st.markdown("### Mix sectoriel des creations d'entreprises")
        add_question_box("Quel tissu economique domine par zone ?")

        sector_cols = available_cols(
            filtered_df,
            [
                "pct_creations_industrie",
                "pct_creations_construction",
                "pct_creations_commerce_transport",
                "pct_creations_info_com",
                "pct_creations_finance",
                "pct_creations_immo",
                "pct_creations_services_admin",
                "pct_creations_adm_sante_social",
                "pct_creations_autres_services",
            ],
        )

        if not sector_cols:
            st.warning("Aucune colonne de creation d'entreprise detectee.")
        else:
            sector_means = filtered_df.groupby("parti_gagnant")[sector_cols].mean()
            sector_100 = sector_means.div(sector_means.sum(axis=1), axis=0) * 100
            sector_100 = sector_100.reset_index()
            sector_long = sector_100.melt(
                id_vars="parti_gagnant",
                value_vars=sector_cols,
                var_name="secteur",
                value_name="part_sectorielle",
            )

            sector_labels = {
                "pct_creations_industrie": "Industrie",
                "pct_creations_construction": "Construction",
                "pct_creations_commerce_transport": "Commerce / transport",
                "pct_creations_info_com": "Info / communication",
                "pct_creations_finance": "Finance",
                "pct_creations_immo": "Immobilier",
                "pct_creations_services_admin": "Services admin",
                "pct_creations_adm_sante_social": "Sante / social",
                "pct_creations_autres_services": "Autres services",
            }

            sector_long["secteur_affiche"] = sector_long["secteur"].map(sector_labels).fillna(
                sector_long["secteur"]
            )
            sector_long["parti_affiche"] = sector_long["parti_gagnant"].apply(format_parti)

            fig_sector = px.bar(
                sector_long,
                x="parti_affiche",
                y="part_sectorielle",
                color="secteur_affiche",
                title="Barres empilees 100 % - mix sectoriel des creations d'entreprises",
                labels={
                    "parti_affiche": "Parti gagnant",
                    "part_sectorielle": "Part sectorielle (%)",
                    "secteur_affiche": "Secteur",
                },
            )
            fig_sector.update_layout(
                barmode="stack",
                yaxis_ticksuffix="%",
                height=650,
            )
            st.plotly_chart(fig_sector, use_container_width=True)

        st.markdown("### Bubble chart - emploi x creations x population")
        add_question_box("Ou investir en priorite ?")

        required_bubble = [
            "pct_emploi_25_49",
            "pct_creations_industrie",
            "population",
            "parti_gagnant",
            "commune",
        ]
        missing_bubble = [col for col in required_bubble if col not in filtered_df.columns]

        if missing_bubble:
            st.warning(f"Colonnes manquantes pour le bubble chart : {missing_bubble}")
        else:
            bubble_df = filtered_df.dropna(
                subset=["pct_emploi_25_49", "pct_creations_industrie"]
            ).copy()
            bubble_df["taille_point"] = (
                bubble_df["population"]
                .fillna(bubble_df["population"].median())
                .clip(lower=1)
            )
            x_range_bubble = compute_zoom_range(
                bubble_df["pct_emploi_25_49"], 0.03, 0.97, 0.12
            )
            y_range_bubble = compute_zoom_range(
                bubble_df["pct_creations_industrie"], 0.02, 0.96, 0.16
            )

            fig_bubble = px.scatter(
                bubble_df,
                x="pct_emploi_25_49",
                y="pct_creations_industrie",
                size="taille_point",
                size_max=46,
                color="parti_gagnant",
                hover_name="commune",
                color_discrete_map=COLOR_MAP,
                title="Emploi 25-49 ans x creations industrielles x population",
                labels={
                    "pct_emploi_25_49": "Taux emploi 25-49 ans",
                    "pct_creations_industrie": "Creations industrie",
                    "parti_gagnant": "Parti gagnant",
                },
                range_x=x_range_bubble,
                range_y=y_range_bubble,
            )
            fig_bubble.update_traces(
                marker=dict(line=dict(width=0.8, color="rgba(255,255,255,0.65)"), opacity=0.88)
            )
            fig_bubble.update_layout(height=650)
            st.plotly_chart(fig_bubble, use_container_width=True)
            st.info(
                "Ce graphique combine l'emploi, la creation industrielle et la population "
                "pour faire ressortir les communes a fort potentiel."
            )


if __name__ == "__main__":
    st.set_page_config(page_title="MSPR - Dashboard analytique territorial", layout="wide")
    build_analytic_dashboard()
