import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def search_issuer_or_isin(df_full, isin_filter=None):
    if isin_filter is not None:
        df_full = df_full[df_full["ISIN"].isin(isin_filter)]

    """
    Affiche un selectbox pour rechercher un ISIN ou un émetteur
    + détails du titre sélectionné
    + tableau des dealers
    + graphique composite (Bid/Mid/Offer + points)
    """

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

