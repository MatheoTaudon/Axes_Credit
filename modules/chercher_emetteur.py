import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from utils.search import search_issuer_or_isin
from scipy.optimize import curve_fit
from scipy.interpolate import UnivariateSpline
from utils.display import bouton_retour_accueil

def nelson_siegel(x, beta0, beta1, beta2, tau):
    term1 = beta0
    term2 = beta1 * (1 - np.exp(-x / tau)) / (x / tau)
    term3 = beta2 * ((1 - np.exp(-x / tau)) / (x / tau) - np.exp(-x / tau))
    return term1 + term2 + term3

def show(df_best):
    bouton_retour_accueil()
    st.markdown("<h2 style='text-align:center; color:orange;'>Chercher un émetteur</h2>", unsafe_allow_html=True)

    df = df_best.copy()
    df["Maturity"] = pd.to_datetime(df["Maturity"], errors="coerce")
    df["Années avant maturité"] = (df["Maturity"] - pd.Timestamp.now()).dt.days / 365
    df["SUB"] = df["Bond ID"].astype(str).str.endswith("SUB") | df["Bond ID"].astype(str).str.endswith("SUB}")

    # Ajout colonne Année de maturité
    df["Année de maturité"] = df["Maturity"].dt.year

    # === RECHERCHE PRINCIPALE : IssuerName – Ticker ===
    df["Issuer_Display"] = df["IssuerName"].astype(str) + " – " + df["Ticker"].astype(str)
    df_issuer_list = df[["IssuerName", "Ticker", "Issuer_Display"]].dropna().drop_duplicates()
    issuer_dict = dict(zip(df_issuer_list["Issuer_Display"], df_issuer_list["Ticker"]))

    selected_display = st.selectbox(
    "Rechercher un groupe émetteur (Issuer – Ticker)",
    [""] + sorted(issuer_dict.keys()),
    index=sorted(issuer_dict.keys()).index("BNP PARIBAS SA – BNP") + 1 if "BNP PARIBAS SA – BNP" in issuer_dict else 0
)

    if not selected_display:
        st.stop()

    selected_ticker = issuer_dict[selected_display]

    # === FILTRAGE PAR TICKER ===
    df_ticker = df[df["Ticker"] == selected_ticker].copy()
    if df_ticker.empty:
        st.warning("Aucun bond trouvé pour ce ticker.")
        st.stop()

    # === MULTISELECT : émetteurs internes avec nombre de titres ===
    issuer_counts = df_ticker["IssuerName"].value_counts()
    options = [f"{issuer} ({issuer_counts[issuer]})" for issuer in issuer_counts.index]
    label_to_issuer = {f"{issuer} ({issuer_counts[issuer]})": issuer for issuer in issuer_counts.index}

    selected_issuer_labels = st.multiselect(
        "Sélectionnez les entités au sein du groupe :",
        options,
        default=options
    )
    selected_issuers = [label_to_issuer[label] for label in selected_issuer_labels]
    df_filtered = df_ticker[df_ticker["IssuerName"].isin(selected_issuers)].copy()

    if df_filtered.empty:
        st.warning("Aucun bond trouvé pour les émetteurs sélectionnés.")
        st.stop()

    # === FILTRES DYNAMIQUES ===
    with st.expander("Filtres"):
        currencies = sorted(df_filtered["Currency"].dropna().unique())
        selected_currency = st.multiselect("Currency", currencies, default=["EUR"] if "EUR" in currencies else currencies)

        sub_sectors = sorted(df_filtered["Sub_Sector"].dropna().unique())
        selected_sub_sector = st.multiselect("Sub-Sector", sub_sectors, default=["IG - SnBnk/Fin"])

        sub_options = ["Subordonnée", "Senior"]
        selected_sub = st.multiselect("Type", sub_options, default=sub_options)

        df_filtered = df_filtered[
            df_filtered["Currency"].isin(selected_currency) &
            df_filtered["Sub_Sector"].isin(selected_sub_sector)
        ]
        if "Subordonnée" not in selected_sub:
            df_filtered = df_filtered[~df_filtered["SUB"]]
        if "Senior" not in selected_sub:
            df_filtered = df_filtered[df_filtered["SUB"]]

        if df_filtered.empty:
            st.warning("Aucun bond après application des filtres.")
            st.stop()

        # === SLIDER MATURITÉ ===
        min_maturity = int(np.floor(df_filtered["Années avant maturité"].min()))
        max_maturity = int(np.ceil(df_filtered["Années avant maturité"].max()))
        selected_range = st.slider("Plage de maturité (en années)", min_value=min_maturity, max_value=max_maturity,
                                   value=(min_maturity, max_maturity), step=1)
        df_filtered = df_filtered[
            df_filtered["Années avant maturité"].between(selected_range[0], selected_range[1])
        ]

        if df_filtered.empty:
            st.warning("Aucun bond dans la plage de maturité sélectionnée.")
            st.stop()

    # === COURBE INTERPOLÉE ===
    st.markdown("### Courbe interpolée des axes")

    y_axis = st.selectbox("Axe Y", ["AXE_Offer_YLD", "AXE_Offer_I-SPD", "AXE_Offer_BMK_SPD", "AXE_Offer_Z-SPD"])
    x_choice = st.selectbox("Axe X", ["Années avant maturité", "Année de maturité"])

    # Préparation des colonnes
    df_filtered["X"] = df_filtered["Années avant maturité"]
    current_year = pd.Timestamp.now().year
    df_filtered["X_display"] = df_filtered["X"] if x_choice == "Années avant maturité" else current_year + df_filtered["X"]
    x_display_title = x_choice

    # Création du graphique
    fig = go.Figure()

    # Points
    fig.add_trace(go.Scatter(
        x=df_filtered["X_display"],
        y=df_filtered[y_axis],
        mode="markers",
        name="Bonds filtrés",
        marker=dict(size=10, color="dodgerblue", symbol="circle"),
        customdata=np.stack([
            df_filtered["ISIN"],
            df_filtered["Bond ID"],
            df_filtered["Maturity"].dt.strftime("%d/%m/%Y"),
            df_filtered[y_axis]
        ], axis=-1),
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>" +
            f"{y_axis} : " + "%{customdata[3]:.2f}<br>" +
            "<span style='font-size:11px; color:gray;'>%{customdata[0]} – %{customdata[2]}</span><extra></extra>"
        )
    ))

    # Courbe
    df_curve = df_filtered[["X", y_axis]].dropna().sort_values("X").drop_duplicates(subset="X")

    if len(df_curve) >= 2:
        x_vals = df_curve["X"].values
        y_vals = df_curve[y_axis].values
        x_smooth = np.linspace(x_vals.min(), x_vals.max(), 300)

        try:
            if len(x_vals) >= 4:
                popt, _ = curve_fit(nelson_siegel, x_vals, y_vals, maxfev=10000)
                y_smooth = nelson_siegel(x_smooth, *popt)
                label = "Courbe interpolée (Nelson-Siegel)"
            else:
                spline = UnivariateSpline(x_vals, y_vals, k=3, s=0.5)
                y_smooth = spline(x_smooth)
                label = "Courbe lissée (Spline cubique)"
        except Exception:
            y_smooth = np.interp(x_smooth, x_vals, y_vals)
            label = "Courbe linéaire"

        x_smooth_display = x_smooth if x_choice == "Années avant maturité" else current_year + x_smooth

        fig.add_trace(go.Scatter(
            x=x_smooth_display,
            y=y_smooth,
            mode="lines",
            name=label,
            line=dict(color="orange", width=3),
            hovertemplate=(
                f"{x_display_title} : %{{x:.1f}}<br>Yield interpolé : %{{y:.2f}}<extra></extra>"
            )
        ))

    fig.update_layout(
        title=f"Courbe interpolée – {selected_ticker}",
        template="plotly_dark",
        xaxis_title=x_display_title,
        yaxis_title=y_axis,
        hovermode="x unified",
        height=700
    )

    st.plotly_chart(fig, use_container_width=True)

    
    st.markdown(
       "<p style='color:gray; font-size:0.8em; text-align:center;'>"
       "Vous pouvez zoomer sur le graphique et double-cliquer pour réinitialiser la vue."
       "</p>",
       unsafe_allow_html=True
    )

    
    st.markdown("### Rechercher un Bond ID")
    df_full = st.session_state.get("df_full_axes")
    if df_full is not None:
        isin_filtered = df_filtered["ISIN"].unique()
        search_issuer_or_isin(df_full, isin_filter=isin_filtered)
    else:
        st.error("Les données complètes ne sont pas chargées. Veuillez revenir à l'accueil.")






        
        

