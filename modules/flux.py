import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_cleaning import bucketize_maturity
from utils.plot import heatmap_qty, bar_flux
from utils.display import bouton_retour_accueil

def show(df):
    bouton_retour_accueil()
    st.markdown(f"<h2 style='text-align:center; color:orange;'>Flux du {datetime.now().strftime('%d/%m/%Y')}</h2>", unsafe_allow_html=True)

    df = st.session_state.get("df_full_axes", df).copy()
    df = bucketize_maturity(df)

    ordered_buckets = [
        "0-1Y", "1-2Y", "2-3Y", "3-4Y", "4-5Y",
        "5-7Y", "7-8Y", "8-10Y", "10-15Y", "15-20Y",
        "20-25Y", "25-30Y", "PERP"
    ]
    df["MaturityBucket"] = pd.Categorical(df["MaturityBucket"], categories=ordered_buckets, ordered=True)

    rating_order = ["Investment Grade", "Crossover", "High Yield", "Junk", "Not Rated"]
    df["Rating_Category"] = pd.Categorical(df["Rating_Category"], categories=rating_order, ordered=True)

    st.markdown("### Heatmap des quantités proposées")
    heatmap_y = st.selectbox("Axe Y (heatmap)", ["Rating_Category", "Sector", "Sub_Sector"])

    pivot = df.groupby([heatmap_y, "MaturityBucket"])["AXE_Offer_QTY"].sum().reset_index().pivot(
        index=heatmap_y, columns="MaturityBucket", values="AXE_Offer_QTY"
    ).reindex(columns=ordered_buckets)

    if pd.api.types.is_categorical_dtype(df[heatmap_y]):
        pivot = pivot.reindex(index=df[heatmap_y].cat.categories)

    fig1 = heatmap_qty(pivot, title=f"Quantité par {heatmap_y} / MaturityBucket")
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### Analyse des flux d'axes")
    x_flux = st.selectbox("Axe X (flux)", ["Sector", "Sub_Sector", "Moody's_rating", "MaturityBucket", "Rating_Category"])
    bar_mode = st.radio("Mode", ["Nombre d’axes", "Quantité totale"])

    if bar_mode == "Nombre d’axes":
        flux_data = df[x_flux].value_counts().reset_index()
        flux_data.columns = [x_flux, "Nombre d'axes"]
        y_col = "Nombre d'axes"
    else:
        flux_data = df.groupby(x_flux)["AXE_Offer_QTY"].sum().reset_index()
        y_col = "AXE_Offer_QTY"

    if x_flux in ["Moody's_rating", "MaturityBucket", "Rating_Category"]:
        if not pd.api.types.is_categorical_dtype(df[x_flux]):
            df[x_flux] = df[x_flux].astype('category')
        flux_data[x_flux] = pd.Categorical(flux_data[x_flux], categories=df[x_flux].cat.categories, ordered=True)
        flux_data = flux_data.sort_values(by=x_flux)

    flux_data = flux_data[flux_data[y_col] > 0]

    fig2 = bar_flux(flux_data, x=x_flux, y=y_col, title=f"{y_col} par {x_flux}")
    st.plotly_chart(fig2, use_container_width=True)



