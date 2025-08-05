import pandas as pd
import streamlit as st

@st.cache_data
def load_mock_data():
    try:
        df_axes = pd.read_excel("BDD_axes.xlsx", sheet_name="Runs")
        df_axes.columns = df_axes.columns.str.strip()
        return df_axes
    except Exception as e:
        st.error(f"Erreur lors du chargement des axes : {e}")
        return pd.DataFrame()

@st.cache_data
def load_mock_portfolio():
    try:
        df_portfolio = pd.read_excel("BDD_axes.xlsx", sheet_name="Portfolio")
        df_portfolio.columns = df_portfolio.columns.str.strip()
        return df_portfolio
    except Exception as e:
        st.error(f"Erreur lors du chargement du portefeuille : {e}")
        return pd.DataFrame()