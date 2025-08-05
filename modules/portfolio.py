import streamlit as st
import pandas as pd
import datetime
from utils.display import bouton_retour_accueil, bouton_export_excel
from utils.plot import afficher_scatter_parametrable
from utils.filters import get_slider_range
from utils.portfolio_processing import reconstituer_portefeuille, get_qty_nette_by_fonds
from utils.data_loader import load_mock_portfolio
from utils.colonnes import colonnes_affichees, colonnes_export

def show(df_best_session):
    bouton_retour_accueil()
    st.markdown("<h2 style='text-align:center; color:orange;'>Portfolio</h2>", unsafe_allow_html=True)

    try:
        df_trades = load_mock_portfolio()
        df_trades.rename(columns=lambda c: c.strip(), inplace=True)
        df_trades.rename(columns={"Isin": "ISIN"}, inplace=True)
    except Exception as e:
        st.error(f"Erreur lors du chargement du portefeuille : {e}")
        return

    am_options = [""] + sorted(df_trades["Asset Manager"].dropna().unique())
    am_selected = st.selectbox("Asset Manager", am_options)
    if not am_selected:
        return

    df_am = df_trades[df_trades["Asset Manager"] == am_selected].copy()
    df_am["Date"] = pd.to_datetime(df_am["Date"], errors="coerce")
    df_am["Qty"] = pd.to_numeric(df_am["Qty"], errors="coerce")
    df_am["Sens"] = df_am["Sens"].str.lower().str.strip()
    df_am["Fonds"] = df_am["Fonds"].astype(str).str.strip()
    df_am = df_am.dropna(subset=["Qty", "Date", "Fonds", "ISIN"])

    st.markdown("### Filtres portefeuille")
    col1, col2 = st.columns([1, 1.2])
    with col1:
        fonds_dispo = sorted(df_am["Fonds"].dropna().unique())
        fonds_selected = st.multiselect("Fonds", fonds_dispo)
        gerants_dispo = sorted(df_am["Gérant"].dropna().unique())
        gerant_selected = st.multiselect("Gérant", gerants_dispo)
        sens_selected = st.multiselect("Dernier sens d'opération", ["buy", "sell"])

    df_filtered = df_am.copy()
    portefeuille = pd.DataFrame()

    with col2:
        min_date = df_am["Date"].min().date()
        date_filter = st.date_input("Date min dernière opération", value=min_date)

        df_filtered = df_filtered[df_filtered["Date"].dt.date >= date_filter]
        if fonds_selected:
            df_filtered = df_filtered[df_filtered["Fonds"].isin(fonds_selected)]
        if gerant_selected:
            df_filtered = df_filtered[df_filtered["Gérant"].isin(gerant_selected)]

        portefeuille = reconstituer_portefeuille(df_filtered)
        if sens_selected:
            portefeuille = portefeuille[portefeuille["Dernier_Sens"].isin(sens_selected)]

        portefeuille = portefeuille[portefeuille["Qty_Nette"] > 0]

        df_axes = st.session_state.get("df_full_axes", pd.DataFrame()).copy()
        df_axes = df_axes[df_axes["ISIN"].isin(portefeuille["ISIN"])]

        nb_dealers = df_axes.groupby("ISIN")["Dealer"].nunique()
        df_valid = df_axes[df_axes["AXE_Offer_QTY"] > 0].copy()
        idx = df_valid.groupby("ISIN")["AXE_Offer_YLD"].idxmax()
        df_best = df_axes.loc[idx].copy()
        df_best.rename(columns={"Dealer": "Best_Dealer"}, inplace=True)
        df_best["Nb_Dealers_AXE"] = df_best["ISIN"].map(nb_dealers)
        df_best = df_best[~((df_best["AXE_Offer_QTY"].fillna(0) == 0) & (df_best["Nb_Dealers_AXE"] == 1))]

        portefeuille_aggrege = portefeuille.groupby("ISIN", as_index=False).agg({
            "Qty_Nette": "sum",
            "Dernier_Sens": "last",
            "Date_Derniere_Op": "max",
            "Nb_Operations": "sum"
        })

        df_best = df_best.merge(portefeuille_aggrege, on="ISIN", how="inner")

        if "Qty_Nette" in df_best.columns and not df_best.empty:
            qty_par_isin = df_best.groupby("ISIN", as_index=False)["Qty_Nette"].sum()
            qty_min, qty_max = get_slider_range(qty_par_isin["Qty_Nette"])
            expo_range = st.slider("Exposition nette (Qty)", qty_min, qty_max, (qty_min, qty_max))
            isins_valides = qty_par_isin[qty_par_isin["Qty_Nette"].between(*expo_range)]["ISIN"]
            df_best = df_best[df_best["ISIN"].isin(isins_valides)]

    if df_best.empty:
        st.warning("Aucune position active ne correspond aux critères.")
        return
    
    # === Filtres AXES ===
    st.markdown("### Filtres sur les axes")
    
    df_axes = st.session_state.get("df_full_axes", pd.DataFrame()).copy()
    df_axes = df_axes[df_axes["ISIN"].isin(portefeuille["ISIN"])].copy()
    df_axes["Maturity"] = pd.to_datetime(df_axes["Maturity"], errors="coerce")
    for col in ["AXE_Offer_YLD", "AXE_Offer_BMK_SPD", "AXE_Offer_QTY", "Axe_Mid_Spread",
                "Composite_Bid_Price", "Composite_Offer_Price"]:
        df_axes[col] = pd.to_numeric(df_axes[col], errors="coerce")
    
    col1, col2 = st.columns(2)
    with col1:
        yld_min, yld_max = get_slider_range(df_axes["AXE_Offer_YLD"])
        yld_range = st.slider("Yield (%)", yld_min, yld_max, (yld_min, yld_max))
        bmk_min, bmk_max = get_slider_range(df_axes["AXE_Offer_BMK_SPD"])
        bmk_range = st.slider("BMK Spread (bps)", bmk_min, bmk_max, (bmk_min, bmk_max))
        qty_min, qty_max = get_slider_range(df_axes["AXE_Offer_QTY"])
        qty_min_input = st.number_input("Quantité AXE min", min_value=0, value=int(qty_min))
    with col2:
        axe_min, axe_max = get_slider_range(df_axes["Axe_Mid_Spread"])
        axe_range = st.slider("Axe vs Mid", axe_min, axe_max, (axe_min, axe_max))
        tol_max = round((df_axes["Composite_Offer_Price"] - df_axes["Composite_Bid_Price"]).abs().max() + 0.1, 2)
        tol = st.slider("Marge autour du Bid/Offer Composite (± points)", 0.0, tol_max, value=tol_max)
        today = datetime.date.today()
        max_date_possible = datetime.date(2100, 12, 31)
        maturity_max = st.date_input(
            "Maturité max",
            value=df_axes["Maturity"].dropna().max().date(),
            min_value=today,
            max_value=max_date_possible
        )
    
    # Filtres actifs uniquement si modifiés
    filtered_axes = df_axes.copy()
    if yld_range != (yld_min, yld_max):
        filtered_axes = filtered_axes[filtered_axes["AXE_Offer_YLD"].between(*yld_range)]
    if bmk_range != (bmk_min, bmk_max):
        filtered_axes = filtered_axes[filtered_axes["AXE_Offer_BMK_SPD"].between(*bmk_range)]
    if qty_min_input > qty_min:
        filtered_axes = filtered_axes[filtered_axes["AXE_Offer_QTY"] >= qty_min_input]
    if axe_range != (axe_min, axe_max):
        filtered_axes = filtered_axes[filtered_axes["Axe_Mid_Spread"].between(*axe_range)]
    
    filtered_axes = filtered_axes[
        (filtered_axes["Maturity"].dt.date <= maturity_max) &
        (filtered_axes["AXE_Offer_Price"] >= filtered_axes["Composite_Bid_Price"] - tol) &
        (filtered_axes["AXE_Offer_Price"] <= filtered_axes["Composite_Offer_Price"] + tol)
    ]
    
    # Recalcul df_best croisé avec portefeuille
    nb_dealers = filtered_axes.groupby("ISIN")["Dealer"].nunique()
    df_valid = filtered_axes[filtered_axes["AXE_Offer_QTY"] > 0].copy()
    idx = df_valid.groupby("ISIN")["AXE_Offer_YLD"].idxmax()
    df_best = filtered_axes.loc[idx].copy()
    df_best.rename(columns={"Dealer": "Best_Dealer"}, inplace=True)
    df_best["Nb_Dealers_AXE"] = df_best["ISIN"].map(nb_dealers)
    df_best = df_best[~((df_best["AXE_Offer_QTY"].fillna(0) == 0) & (df_best["Nb_Dealers_AXE"] == 1))]
    
    portefeuille_aggrege = portefeuille.groupby("ISIN", as_index=False).agg({
        "Qty_Nette": "sum",
        "Dernier_Sens": "last",
        "Date_Derniere_Op": "max",
        "Nb_Operations": "sum"
    })
    df_best = df_best.merge(portefeuille_aggrege, on="ISIN", how="inner")
    
    if "Maturity" in df_best.columns:
        df_best["Maturity"] = pd.to_datetime(df_best["Maturity"], errors="coerce").dt.strftime("%Y/%m/%d")
    if "Date_Derniere_Op" in df_best.columns:
        df_best["Date_Derniere_Op"] = pd.to_datetime(df_best["Date_Derniere_Op"], errors="coerce").dt.strftime("%Y/%m/%d")

    st.markdown(f"### Résultats pour {am_selected} ({len(df_best)} lignes)")
    colonnes_affichees_finales = [col for col in colonnes_affichees if col in df_best.columns]
    st.dataframe(df_best[colonnes_affichees_finales], use_container_width=True)

    colonnes_exportables = [col for col in colonnes_export if col in df_best.columns]
    bouton_export_excel(df_best[colonnes_exportables], nom_fichier="axes_croises.xlsx", nom_feuille="Axes croisés")
        
    st.markdown("### Visualisation des axes")
    afficher_scatter_parametrable(df_best)

    # === Recherche ISIN ===
    st.markdown("### Rechercher un Bond ID ou un Émetteur")
    df_full = st.session_state.get("df_full_axes")
    if df_full is not None:
        isin_filter = df_best["ISIN"].unique().tolist()
        df_full = df_full[df_full["ISIN"].isin(isin_filter)]

        options = df_full[["IssuerName", "Bond ID", "ISIN"]].dropna().astype(str).drop_duplicates()
        options["Label"] = options["Bond ID"] + " – " + options["IssuerName"]
        combo_dict = dict(zip(options["Label"], options["ISIN"]))
        selected = st.selectbox("Commencez à taper le Bond ID:", [""] + sorted(combo_dict))

        if selected:
            selected_isin = combo_dict[selected]
            subset = df_full[df_full["ISIN"] == selected_isin]

            if not subset.empty:
                bond = subset.iloc[0]

                st.markdown("#### Infos du titre")
                infos = {
                    "Bond ID": bond.get("Bond ID"),
                    "Émetteur": bond.get("IssuerName"),
                    "ISIN": bond.get("ISIN"),
                    "Maturité": bond.get("Maturity"),
                    "Devise": bond.get("Currency"),
                    "Coupon": bond.get("Coupon"),
                    "CouponType": bond.get("CouponType"),
                    "Secteur": bond.get("Sector"),
                    "Notation Moody's": bond.get("Moody's_rating")
                }
                st.table(pd.DataFrame.from_dict(infos, orient='index', columns=["Valeur"]))

                summary_df, detail_dict = get_qty_nette_by_fonds(df_filtered, selected_isin)
                summary_df = summary_df[summary_df["Qty_Nette"] > 0]
                
                if not summary_df.empty:
                    st.markdown("#### Informations portefeuille")
                    if "Date_Derniere_Op" in summary_df.columns:
                        summary_df["Date_Derniere_Op"] = pd.to_datetime(summary_df["Date_Derniere_Op"], errors="coerce").dt.strftime("%d/%m/%Y")
                    st.dataframe(summary_df[[
                        "Fonds", "Qty_Nette", "Nb_Operations", "Dernier_Sens", "Date_Derniere_Op", "Dernier_Gerant"
                    ]], use_container_width=True)
                
                    all_details = pd.concat(detail_dict.values(), ignore_index=True)
                

                    all_details.columns = all_details.columns.str.strip().str.upper()
                    all_details = all_details[all_details["QTY"] > 0]
                
                    if not all_details.empty:
                        with st.expander("Voir le détail de toutes les opérations"):
                            colonnes = [col for col in ["FONDS", "SENS", "EXEC_PRICE", "QTY", "DATE", "GÉRANT"] if col in all_details.columns]
                            all_details["DATE"] = pd.to_datetime(all_details["DATE"], errors="coerce").dt.strftime("%Y/%m/%d")
            
                
                            st.dataframe(all_details[colonnes], use_container_width=True)

                dealer_col = "Dealer" if "Dealer" in subset.columns else "Best_Dealer"
                subset_sorted = subset.sort_values(by="Axe_Mid_Spread", ascending=True)
                subset_unique = subset_sorted.drop_duplicates(subset=[dealer_col, "ISIN"], keep="first")

                colonnes = [
                    dealer_col, "AXE_Offer_Price", "AXE_Offer_YLD","AXE_Offer_BMK_SPD","AXE_Offer_QTY",
                    "Composite_Bid_Price", "Composite_Offer_Price", "Axe_Mid_Spread",
                    "AXE_Offer_Z-SPD", "AXE_Offer_I-SPD", "AXE_Offer_ASW"
                ]
                colonnes = [col for col in colonnes if col in subset_unique.columns]
                df_dealers = subset_unique[colonnes].copy()
                df_dealers.rename(columns={dealer_col: "Dealer"}, inplace=True)

                st.markdown("#### Dealers axés sur ce titre")
                st.dataframe(df_dealers, use_container_width=True)

                st.markdown("#### Visualisation fourchette composite")
                import plotly.graph_objects as go
                bid = bond.get("Composite_Bid_Price")
                offer = bond.get("Composite_Offer_Price")
                mid = bond.get("Mid_Price")

                fig = go.Figure()
                if pd.notna(bid) and pd.notna(offer):
                    fig.add_shape(type="line", x0=bid, x1=offer, y0=0, y1=0, line=dict(color="orange", width=3))

                for val, label in zip([bid, mid, offer], ["Bid", "Mid", "Offer"]):
                    if pd.notna(val):
                        fig.add_shape(type="line", x0=val, x1=val, y0=-0.3, y1=0.4,
                                      line=dict(color="orange", width=2))
                        fig.add_annotation(x=val, y=-0.3, text=label, showarrow=False,
                                           font=dict(color="orange"), yanchor="top")

                for _, row in subset_unique.iterrows():
                    if pd.notna(row["AXE_Offer_Price"]):
                        fig.add_trace(go.Scatter(
                            x=[row["AXE_Offer_Price"]],
                            y=[0],
                            mode="markers+text",
                            text=row.get(dealer_col, "Dealer"),
                            textposition="top center",
                            marker=dict(size=15)
                        ))

                fig.update_layout(
                    height=250,
                    template="plotly_dark",
                    showlegend=False,
                    xaxis_title="Prix",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(visible=False)
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Les données complètes ne sont pas chargées. Veuillez revenir à l'accueil.")


    