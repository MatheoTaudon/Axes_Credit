import streamlit as st
import pandas as pd
from utils.display import bouton_retour_accueil, bouton_export_excel
from utils.plot import afficher_scatter_parametrable
from utils.search import search_issuer_or_isin
from utils.colonnes import colonnes_affichees, colonnes_export

def show(df_best_session):
    df_best = df_best_session.copy()
    bouton_retour_accueil()
    st.markdown("<h2 style='text-align:center; color:orange;'>Wichlist</h2>", unsafe_allow_html=True)

    # === Upload fichier ===
    st.markdown("### Import de fichier")
    st.info(
        "**Format attendu :**\n"
        "- Colonne A = liste des **ISIN** (sans titre)\n"
        "- Colonne B = liste des **Ticker** (sans titre)\n"
        "- Les colonnes ISIN et ticker sont independantes, Vous pouvez laisser une des deux colonnes vide selon le mode de croisement choisi\n\n"
        " **Pas besoin d'en-tête**. Commencez directement à coller les ISIN en A1 et/ou les Ticker en B1."
    )

    if "df_import" not in st.session_state:
        fichier = st.file_uploader("Importer un fichier Excel (sans en-tête)", type=["xlsx"])
        if fichier:
            try:
                df_import = pd.read_excel(fichier, header=None, usecols=[0, 1])
                df_import.columns = ["ISIN", "Ticker"]
                st.session_state["df_import"] = df_import
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier : {e}")
                return
        else:
            return
    else:
        df_import = st.session_state["df_import"]
        st.success("Fichier précédemment importé chargé depuis la session.")

    if st.button("Réinitialiser le fichier importé"):
        st.session_state.pop("df_import", None)
        st.rerun()

    # === Choix croisement ===
    st.markdown("### Méthode de croisement")
    mode = st.radio("Croiser selon :", ["ISIN", "Ticker"], horizontal=True)
    colonne_reference = "ISIN" if mode == "ISIN" else "Ticker"

    if colonne_reference not in df_import.columns:
        st.error(f" La colonne '{colonne_reference}' est absente.")
        return

    df_best = st.session_state.get("df", pd.DataFrame()).copy()
    if df_best.empty:
        st.error("⚠️ Aucun axe disponible. Reviens à l’accueil pour charger les données.")
        return

    valeurs_importees = df_import[colonne_reference].dropna().astype(str).str.strip().unique()
    df_croise = df_best[df_best[colonne_reference].astype(str).str.strip().isin(valeurs_importees)]

    if df_croise.empty:
        st.warning("Aucun axe ne correspond à la liste importée.")
        return

    # === Affichage résultats ===
    st.markdown(f"### Axes croisés : {len(df_croise)} ligne(s)")

    colonnes_affichees_finales = [col for col in colonnes_affichees if col in df_croise.columns]
    st.dataframe(df_croise[colonnes_affichees_finales], use_container_width=True)

    # Export Excel avec colonnes spécifiques
    colonnes_exportables = [col for col in colonnes_export if col in df_croise.columns]
    bouton_export_excel(df_croise[colonnes_exportables], nom_fichier="axes_croises.xlsx", nom_feuille="Axes croisés")

    # === Scatter Plot ===
    st.markdown("### Visualisation des axes")
    afficher_scatter_parametrable(df_croise)

    # === Recherche ISIN ou Émetteur ===
    st.markdown("### Rechercher un Bond ID ou un Émetteur")
    df_full = st.session_state.get("df_full_axes")
    if df_full is not None:
        isin_filter = df_croise["ISIN"].unique().tolist()
        search_issuer_or_isin(df_full, isin_filter=isin_filter)
    else:
        st.warning("Le détail complet des axes n’est pas chargé. Veuillez revenir à l’accueil.")















