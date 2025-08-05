import streamlit as st
from modules import accueil, portfolio, filtrer_les_axes, chercher_emetteur, flux, Whichlist

st.set_page_config(layout="wide", page_title="AXES Crédit")

if "page" not in st.session_state:
    st.session_state.page = "accueil"

if st.session_state.page == "accueil":
    accueil.show()
elif st.session_state.page == "portfolio":
    portfolio.show(st.session_state.df) 
elif st.session_state.page == "filtrer_les_axes":
    filtrer_les_axes.show(st.session_state.df)  
elif st.session_state.page == "chercher_emetteur":
    chercher_emetteur.show(st.session_state.df) 
elif st.session_state.page == "Whichlist":
    Whichlist.show(st.session_state.df) 
elif st.session_state.page == "flux":
    flux.show(st.session_state.df_full_axes)  
