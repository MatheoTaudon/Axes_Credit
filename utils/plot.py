import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# === Ajoute une colonne de positionnement par rapport à la fourchette composite ===
def calcul_zone_composite(df):
    if "Zone Composite" in df.columns:
        return df

    def zone(row):
        try:
            bid = row["Composite_Bid_Price"]
            offer = row["Composite_Offer_Price"]
            axe = row["AXE_Offer_Price"]
            mid = (bid + offer) / 2
            if pd.isna(axe) or pd.isna(bid) or pd.isna(offer):
                return None
            if axe > offer:
                return "> Offer"
            elif axe > mid:
                return "Mid-Offer"
            elif axe >= bid:
                return "Bid-Mid"
            else:
                return "< Bid"
        except:
            return None

    df["Zone Composite"] = df.apply(zone, axis=1)
    return df

def afficher_scatter_parametrable(df, titre="Graphique AXES (paramétrable)", hauteur=600):
    df = df.copy()
    df = calcul_zone_composite(df)

    # Forcer conversion propre de Maturity sans écraser les NaT valides
    if "Maturity" in df.columns:
        df["Maturity"] = pd.to_datetime(df["Maturity"], errors="coerce")
    if "Années avant maturité" not in df.columns:
        df["Années avant maturité"] = (df["Maturity"] - pd.Timestamp.now()).dt.days / 365

    options_x = ["Années avant maturité", "AXE_Offer_Price", "AXE_Offer_YLD"]
    options_y = ["AXE_Offer_BMK_SPD", "AXE_Offer_Z-SPD", "AXE_Offer_I-SPD", "AXE_Offer_ASW", "AXE_Offer_YLD", "AXE_Offer_Price"]
    options_color = ["Zone Composite", "Rating_Category", "Sector", "Sub_Sector", "Currency"]

    with st.expander("Paramétrage du graphique"):
        x_axis = st.selectbox("Axe X", options_x, index=0)
        y_axis = st.selectbox("Axe Y", options_y, index=options_y.index("AXE_Offer_YLD"))
        color = st.selectbox("Couleur", options_color, index=0)

    hover = ["Bond ID", "IssuerName", "AXE_Offer_QTY", "AXE_Offer_YLD", "AXE_Offer_Price"]

    color_map = {
        "> Offer": "#FF4C4C",
        "Mid-Offer": "#FFA500",
        "Bid-Mid": "#4CAF50",
        "< Bid": "#1E90FF"
    } if color == "Zone Composite" else None

    # On ne filtre que les X et Y nécessaires
    df_plot = df[df[x_axis].notna() & df[y_axis].notna()]

    fig = px.scatter(
        df_plot,
        x=x_axis,
        y=y_axis,
        color=color,
        color_discrete_map=color_map,
        hover_data=hover,
        height=hauteur,
        template="plotly_dark"
    )
    fig.update_traces(marker=dict(size=9, opacity=0.85, line=dict(width=0.5, color="white")))
    fig.update_layout(title=titre)

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
       "<p style='color:gray; font-size:0.8em; text-align:center;'>"
       "Vous pouvez zoomer sur le graphique et double-cliquer pour réinitialiser la vue."
       "</p>",
       unsafe_allow_html=True
    )

# === Heatmap à partir d’un pivot quantité ===
def heatmap_qty(df_pivot, title="Heatmap des quantités"):
    fig = px.imshow(
        df_pivot.fillna(0),
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Viridis",
        title=title
    )
    fig.update_layout(template="plotly_dark")
    return fig

# === Bar chart (flux par catégorie ou quantité) ===
def bar_flux(df, x, y, title=""):
    fig = px.bar(
        df,
        x=x,
        y=y,
        text_auto=True,
        title=title,
        color_discrete_sequence=["#1f77b4"],
        template="plotly_dark"
    )
    return fig