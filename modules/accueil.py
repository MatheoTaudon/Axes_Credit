import streamlit as st
from utils.data_loader import load_mock_data
from utils.data_cleaning import clean_full_dataframe
from utils.display import bouton_export_excel, message_legal_axes
from utils.colonnes import colonnes_affichees, colonnes_export 

def show():
    # === POPUP D’INTRODUCTION (affichée une seule fois) ===
    if "intro_shown" not in st.session_state:
        st.session_state.intro_shown = True
        with st.expander("Ce projet est une reconstitution – cliquez pour plus d’infos", expanded=False):
            st.markdown("""
            ### Reconstitution du projet lors de mon stage Exoé

            Cette app est une **démo fonctionnelle** basée sur un **fichier Excel fictif**.  
            La version originale fonctionne via une **connexion SQL live**.

            ---
            #### Modules disponibles :

            - **Portfolio** : croisement des axes disponibles avec ceux déjà traités  
            - **Filtrer les axes** : filtre dynamique des axes selon critères qualitatifs et quantitatifs  
            - **Chercher un émetteur** : visualisation des axes d’un émetteur + courbe interpolée  
            - **Whichlist** : importer une liste d’ISIN/Ticker à croiser avec la base  
            - **Flux** : observer la répartition de la liquidité (quantité, dealers, profondeur...)

            ---
            ⚠️ Données purement fictives – usage démonstratif uniquement.
            """)

    st.markdown("<h1 style='text-align:center; color:orange;'>Axes Crédit</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Bienvenue, sélectionnez une analyse :</p>", unsafe_allow_html=True)

    df_raw = load_mock_data()
    if df_raw.empty:
        st.warning("Aucune donnée trouvée.")
        return

    # Nettoyage complet avec formatage homogène
    df_full_axes, df_best, last_import = clean_full_dataframe(df_raw)

    # Stockage dans session
    st.session_state.df_full_axes = df_full_axes
    st.session_state.df = df_best

    # Navigation boutons
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Portfolio"):
            st.session_state.page = "portfolio"
            st.rerun()
    with col2:
        if st.button("Filtrer les axes"):
            st.session_state.page = "filtrer_les_axes"
            st.rerun()
    with col3:
        if st.button("Chercher un Émetteur"):
            st.session_state.page = "chercher_emetteur"
            st.rerun()
    with col4:
        if st.button("Wichlist"):
            st.session_state.page = "Whichlist"
            st.rerun()
    with col5:
        if st.button("Flux"):
            st.session_state.page = "flux"
            st.rerun()

    # Affichage tableau
    st.markdown(f"### Axes du {last_import.strftime('%d/%m/%Y à %H:%M')} ({len(df_best):,} lignes)")

    colonnes_visibles = [col for col in colonnes_affichees if col in df_best.columns and col != "Stream_Offer_Price"]
    st.dataframe(df_best[colonnes_visibles], use_container_width=True)

    # Export Excel avec colonnes spécifiques
    colonnes_exportables = [col for col in colonnes_export if col in df_best.columns]
    bouton_export_excel(df_best[colonnes_exportables], nom_fichier=f"Axes_export_{last_import.strftime('%Y%m%d')}.xlsx", nom_feuille="Axes")

    # Avertissement légal
    message_legal_axes()
