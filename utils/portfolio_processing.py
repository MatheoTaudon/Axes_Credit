import pandas as pd

def reconstituer_portefeuille(df_trades: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les positions nettes (buy = +Qty, sell = -Qty) par ISIN et Fonds,
    et récupère le dernier sens, date et gérant pour chaque couple.
    """
    df = df_trades.copy()
    df.columns = df.columns.str.strip()
    df.rename(columns={"Isin": "ISIN"}, inplace=True)

    if "ISIN" not in df.columns:
        raise RuntimeError("Colonne 'ISIN' manquante dans les données portefeuille.")

    df = df.dropna(subset=["ISIN", "Qty", "Sens", "Date", "Fonds"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["Sens"] = df["Sens"].str.lower().str.strip()
    df["Fonds"] = df["Fonds"].astype(str).str.strip()

    df["Qty_Signee"] = df.apply(lambda row: row["Qty"] if row["Sens"] == "buy" else -row["Qty"], axis=1)

    portefeuille = df.groupby(["ISIN", "Fonds"]).agg(
        Qty_Nette=("Qty_Signee", "sum"),
        Nb_Operations=("ISIN", "count"),
        Date_Derniere_Op=("Date", "max"),
        Dernier_Sens=("Sens", "last"),
        Dernier_Gerant=("Gérant", "last"),
        Asset_Manager=("Asset Manager", "last")
    ).reset_index()

    portefeuille = portefeuille[portefeuille["Qty_Nette"] != 0]

    return portefeuille


def get_qty_nette_by_fonds(df_trades: pd.DataFrame, isin: str):
    """
    Pour un ISIN donné, retourne :
    - un résumé par fonds (qty nette, nb opérations, dernier sens, date, gérant)
    - un dictionnaire {fonds: détail des opérations}
    """
    df = df_trades.copy()
    df.columns = df.columns.str.strip()
    df.rename(columns={"Isin": "ISIN"}, inplace=True)
    df = df[df["ISIN"] == isin].copy()

    if df.empty:
        return pd.DataFrame(), {}

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
    df["Sens"] = df["Sens"].str.lower().str.strip()
    df["Fonds"] = df["Fonds"].astype(str).str.strip()

    df["Qty_Signee"] = df.apply(lambda row: row["Qty"] if row["Sens"] == "buy" else -row["Qty"], axis=1)

    summary = (
        df.groupby("Fonds", as_index=False).agg({
            "Qty_Signee": "sum",
            "ISIN": "count",
            "Sens": "last",
            "Date": "max",
            "Gérant": "last"
        }).rename(columns={
            "Qty_Signee": "Qty_Nette",
            "ISIN": "Nb_Operations",
            "Sens": "Dernier_Sens",
            "Date": "Date_Derniere_Op",
            "Gérant": "Dernier_Gerant"
        })
    )
    colonnes_detail = ["Fonds", "Qty", "Date", "Sens", "Gérant", "EXEC_PRICE"]
    colonnes_detail = [col for col in colonnes_detail if col in df.columns]

    detail_dict = {
        fonds: df[df["Fonds"] == fonds][colonnes_detail].copy()
        for fonds in summary["Fonds"]
    }

    return summary, detail_dict

