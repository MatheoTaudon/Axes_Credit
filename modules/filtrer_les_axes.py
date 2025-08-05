import streamlit as st
import pandas as pd
import datetime
from utils.filters import get_slider_range
from utils.plot import afficher_scatter_parametrable
from utils.search import search_issuer_or_isin
from utils.display import bouton_retour_accueil, bouton_export_excel
from utils.colonnes import colonnes_affichees, colonnes_export 


def show(df):
    bouton_retour_accueil()
    st.markdown("<h2 style='text-align:center; color:orange;'>Filtrer les axes</h2>", unsafe_allow_html=True)

    df = st.session_state.get("df", df).copy()

    st.markdown("### Filtres")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### Critères qualitatifs")
        selected_sectors = st.multiselect("Secteurs", sorted(df["Sector"].dropna().unique()))
        selected_currencies = st.multiselect("Devises", sorted(df["Currency"].dropna().unique()))
        selected_ratings = st.multiselect("Notation crédit", sorted(df["Rating_Category"].dropna().unique()))
        selected_tickers = st.multiselect("Filtrer par Ticker", sorted(df["Ticker"].dropna().unique()))
        selected_dealers = st.multiselect("Filtrer par Dealer", sorted(df["Best_Dealer"].dropna().unique()))

    with col2:
        st.markdown("##### Critères quantitatifs")
        yld_min, yld_max = get_slider_range(df["AXE_Offer_YLD"])
        yld_range = st.slider("Yield (%)", yld_min, yld_max, (yld_min, yld_max))

        bmk_min, bmk_max = get_slider_range(df["AXE_Offer_BMK_SPD"])
        bmk_range = st.slider("Spread BMK (bps)", bmk_min, bmk_max, (bmk_min, bmk_max))
        
        dealer_min, dealer_max = get_slider_range(df["Nb_Dealers_AXE"])
        dealer_min = int(dealer_min)
        dealer_max = int(dealer_max)
        dealer_range = st.slider ("Nb Dealers", dealer_min, dealer_max, (dealer_min, dealer_max), step=1)

        qty_min, qty_max = get_slider_range(df["AXE_Offer_QTY"])
        qty_min_input = st.number_input("Quantité minimum", qty_min, qty_max, value=qty_min)
        qty_max_input = st.number_input("Quantité maximum", qty_min_input, qty_max, value=qty_max)

    with col3:
        st.markdown("##### Options avancées")
        axe_min, axe_max = get_slider_range(df["Axe_Mid_Spread"])
        axe_spread_range = st.slider("Axe vs Mid", axe_min, axe_max, (axe_min, axe_max))

        df["comp_gap"] = (df["Composite_Offer_Price"] - df["Composite_Bid_Price"]).abs()
        tol_max = round(min(df["comp_gap"].max() + 0.1, 5.0), 2)
        tol = st.slider("Marge autour du Bid/Offer Composite (± points)", 0.0, tol_max, value=tol_max, step=0.01)

        exclude_144a = st.checkbox("Exclure les titres 144A")


        def safe_date(d):
            if hasattr(d, 'date'):
                return d.date()
            return d
        
        streamlit_min = datetime.date(1970, 1, 1)
        streamlit_max = datetime.date(2100, 12, 31)
        
        min_maturity = safe_date(df["Maturity"].min())
        max_maturity = safe_date(df["Maturity"].max())
        
        safe_min = max(min_maturity, streamlit_min)
        safe_max = min(max_maturity, streamlit_max)
        
        maturity_min = st.date_input("Maturité min", safe_min, min_value=streamlit_min, max_value=safe_max)
        maturity_max = st.date_input("Maturité max", safe_max, min_value=maturity_min, max_value=streamlit_max)

    # === Filtrage dynamique sans exclure les NaN tant que non modifié ===
    filtered_df = df.copy()

    if yld_range != (yld_min, yld_max):
        filtered_df = filtered_df[
            filtered_df["AXE_Offer_YLD"].notna() &
            filtered_df["AXE_Offer_YLD"].between(*yld_range)
        ]

    if bmk_range != (bmk_min, bmk_max):
        filtered_df = filtered_df[
            filtered_df["AXE_Offer_BMK_SPD"].notna() &
            filtered_df["AXE_Offer_BMK_SPD"].between(*bmk_range)
        ]
        
    if dealer_range != (dealer_min, dealer_max):
        filtered_df = filtered_df[
            filtered_df["Nb_Dealers_AXE"].notna() &
            filtered_df["Nb_Dealers_AXE"].between(*dealer_range)
        ]

    if (qty_min_input != qty_min) or (qty_max_input != qty_max):
        filtered_df = filtered_df[
            filtered_df["AXE_Offer_QTY"].notna() &
            filtered_df["AXE_Offer_QTY"].between(qty_min_input, qty_max_input)
        ]

    if axe_spread_range != (axe_min, axe_max):
        filtered_df = filtered_df[
            filtered_df["Axe_Mid_Spread"].notna() &
            filtered_df["Axe_Mid_Spread"].between(*axe_spread_range)
        ]

    if (maturity_min != safe_min) or (maturity_max != safe_max):
        filtered_df = filtered_df[
            filtered_df["Maturity"].notna() &
            filtered_df["Maturity"].between(maturity_min, maturity_max)
        ]

    # === Filtres qualitatifs ===
    if selected_sectors:
        filtered_df = filtered_df[filtered_df["Sector"].isin(selected_sectors)]
    if selected_currencies:
        filtered_df = filtered_df[filtered_df["Currency"].isin(selected_currencies)]
    if selected_ratings:
        filtered_df = filtered_df[filtered_df["Rating_Category"].isin(selected_ratings)]
    if selected_tickers:
        filtered_df = filtered_df[filtered_df["Ticker"].isin(selected_tickers)]
    if selected_dealers:
        filtered_df = filtered_df[filtered_df["Best_Dealer"].isin(selected_dealers)]
    if exclude_144a:
        filtered_df = filtered_df[~filtered_df["Bond ID"].astype(str).str.contains("144A")]
  
    # === Tolérance composite ===
    filtered_df = filtered_df[
        (filtered_df["AXE_Offer_Price"] >= filtered_df["Composite_Bid_Price"] - tol) &
        (filtered_df["AXE_Offer_Price"] <= filtered_df["Composite_Offer_Price"] + tol)
    ]

    st.markdown(f"### Résultats filtrés ({len(filtered_df)} lignes)")

    colonnes_affichees_finales = [col for col in colonnes_affichees if col in filtered_df.columns]
    st.dataframe(filtered_df[colonnes_affichees_finales], use_container_width=True)

    # Export Excel avec colonnes spécifiques
    colonnes_exportables = [col for col in colonnes_export if col in filtered_df.columns]
    bouton_export_excel(filtered_df[colonnes_exportables], nom_fichier="Axes_export.xlsx", nom_feuille="Axes")

    st.markdown("### Clustering des résultats filtrés")
    afficher_scatter_parametrable(filtered_df)

    st.markdown("### Rechercher un Bond ID ou un Émetteur")
    df_full = st.session_state.get("df_full_axes")
    if df_full is not None:
        isin_filtered = filtered_df["ISIN"].unique()
        search_issuer_or_isin(df_full, isin_filter=isin_filtered)
    else:
        st.error("Les données complètes ne sont pas chargées. Veuillez revenir à l'accueil.")


