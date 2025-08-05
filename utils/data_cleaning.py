import pandas as pd
import numpy as np

def classify_rating_category(row):
    fitch = str(row.get("FitchRating", "")).strip().upper()
    moodys = str(row.get("Moody's_rating", "")).strip().upper()
    invalid = {"", "N/A", "NR", "NOT RATED", "WD", "WR", "NAN"}

    if fitch not in invalid:
        rating = fitch
    elif moodys not in invalid:
        rating = moodys
    else:
        return "Not Rated"

    investment_grade = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "A1", "A2", "A3",
                        "AA1", "AA2", "AA3", "Aaa", "Aa1", "Aa2", "Aa3"}
    crossover = {"BBB+", "BBB", "BBB-", "BAA1", "BAA2", "BAA3", "BB+", "BB", "BB-"}
    high_yield = {"B+", "B", "B-", "B1", "B2", "B3", "BA1", "BA2", "BA3"}
    junk = {"CCC+", "CCC", "CCC-", "CC", "C", "CA", "CAA1", "CAA2", "CAA3"}

    if rating in investment_grade:
        return "Investment Grade"
    elif rating in crossover:
        return "Crossover"
    elif rating in high_yield:
        return "High Yield"
    elif rating in junk:
        return "Junk"
    return "Not Rated"

def clean_full_dataframe(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df.rename(columns={
        "Issuer name": "IssuerName",
        "Isin": "ISIN",
        "Coupon type": "CouponType",
        "Fitch rating": "FitchRating",
        "Moody's rating": "Moody's_rating"
    }, inplace=True)

    df["ImportDateTime"] = pd.to_datetime(df["ImportDateTime"], errors="coerce")
    df = df[df["ImportDateTime"].notna()]
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.Timestamp.now()

    last_import = df["ImportDateTime"].max()
    df = df[df["ImportDateTime"] == last_import]

    df.rename(columns={
        "IA_Offer_Price": "AXE_Offer_Price",
        "IA_Offer_YLD": "AXE_Offer_YLD",
        "IA_Offer_QTY": "AXE_Offer_QTY",
        "IA_Offer_BMK_SPD": "AXE_Offer_BMK_SPD",
        "IA_Offer_I-SPD": "AXE_Offer_I-SPD",
        "IA_Offer_Z-SPD": "AXE_Offer_Z-SPD",
        "IA_Offer_ASW": "AXE_Offer_ASW"
    }, inplace=True)

    df["AXE_Offer_QTY"] = df["AXE_Offer_QTY"].astype(str).str.replace(" ", "").str.replace(",", "")
    df["AXE_Offer_QTY"] = pd.to_numeric(df["AXE_Offer_QTY"], errors="coerce") * 1000

    df["AXE_Offer_YLD"] = df["AXE_Offer_YLD"].astype(str).str.replace("%", "").str.replace(",", ".")
    df["AXE_Offer_YLD"] = pd.to_numeric(df["AXE_Offer_YLD"], errors="coerce").abs()

    for col in ["AXE_Offer_Price", "AXE_Offer_BMK_SPD", "AXE_Offer_I-SPD", "AXE_Offer_Z-SPD", "AXE_Offer_ASW"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Stream_Offer_Price" in df.columns and "Stream_Offer_YLD" in df.columns:
        df["Stream_Offer_Price"] = df["Stream_Offer_Price"].astype(str).str.replace(" ", "").str.replace(",", ".")
        df["Stream_Offer_Price"] = pd.to_numeric(df["Stream_Offer_Price"], errors="coerce")

        df["Stream_Offer_YLD"] = df["Stream_Offer_YLD"].astype(str).str.replace("%", "").str.replace(",", ".")
        df["Stream_Offer_YLD"] = pd.to_numeric(df["Stream_Offer_YLD"], errors="coerce")

        diff_price = (df["AXE_Offer_Price"] - df["Stream_Offer_Price"]).abs()
        condition_update = (
            df["Stream_Offer_Price"].notna() & df["Stream_Offer_YLD"].notna() &
            df["AXE_Offer_Price"].notna() & df["AXE_Offer_YLD"].notna() &
            (diff_price > 10)
        )
        df.loc[condition_update, "AXE_Offer_Price"] = df.loc[condition_update, "Stream_Offer_Price"]
        df.loc[condition_update, "AXE_Offer_YLD"] = df.loc[condition_update, "Stream_Offer_YLD"]

    cond_nan_stream = df["Stream_Offer_Price"].isna()
    cond_yld_gt_price = (df["AXE_Offer_YLD"] - df["AXE_Offer_Price"]) > 30
    cond_swap = cond_nan_stream & cond_yld_gt_price
    df.loc[cond_swap, ["AXE_Offer_Price", "AXE_Offer_YLD"]] = df.loc[cond_swap, ["AXE_Offer_YLD", "AXE_Offer_Price"]].values

    df = df[(df["AXE_Offer_Price"] != 0) & (df["AXE_Offer_Price"] <= 150) & (df["AXE_Offer_YLD"] <= 70)]
    df.dropna(subset=["AXE_Offer_Price", "AXE_Offer_YLD", "AXE_Offer_QTY"], inplace=True)

    if "TW_Offer_Price" in df.columns and "TW_Bid_Price" in df.columns:
        df["Composite_Offer_Price"] = pd.to_numeric(df["TW_Offer_Price"], errors="coerce")
        df["Composite_Bid_Price"] = pd.to_numeric(df["TW_Bid_Price"], errors="coerce")
        df["Mid_Price"] = (df["Composite_Offer_Price"] + df["Composite_Bid_Price"]) / 2
        df["Axe_Mid_Spread"] = df["AXE_Offer_Price"] - df["Mid_Price"]
    else:
        df["Composite_Offer_Price"] = df["Composite_Bid_Price"] = df["Mid_Price"] = df["Axe_Mid_Spread"] = np.nan

    # formats et arrondis 

    df["Maturity"] = pd.to_datetime(df["Maturity"], errors="coerce")
    limite = pd.Timestamp("2100-01-01")
    fictive = pd.Timestamp("2099-12-31")
    df["Maturity"] = df["Maturity"].apply(lambda d: fictive if pd.isna(d) or (d > limite) else d)
    df["Maturity"] = df["Maturity"].dt.date

    for col in ["AXE_Offer_Price", "AXE_Offer_YLD", "AXE_Offer_QTY", "Composite_Offer_Price",
                "Composite_Bid_Price", "Mid_Price", "Axe_Mid_Spread"]:
        if col in df.columns:
            df[col] = df[col].round(2)
    for col in ["AXE_Offer_BMK_SPD", "AXE_Offer_Z-SPD", "AXE_Offer_I-SPD", "AXE_Offer_ASW"]:
        if col in df.columns:
            df[col] = df[col].round(0)

    # Sector / Sub_Sector et rating category
    df["Sub_Sector"] = df["Sector"]
    df["Sector"] = df["Sub_Sector"].str.extract(r'^([^ -]+)')
    df["Sector"] = df.apply(
        lambda row: "IG FIN" if isinstance(row["Sub_Sector"], str) and row["Sub_Sector"].startswith("IG") and any(
            x in row["Sub_Sector"] for x in ["CoCo", "Lower Tier", "Upper T2", "SnBnk"])
        else "IG CORPO" if isinstance(row["Sub_Sector"], str) and row["Sub_Sector"].startswith("IG")
        else row["Sector"], axis=1)

    df["Rating_Category"] = df.apply(classify_rating_category, axis=1)

    df_full_axes = df.copy()
    nb_dealers = df_full_axes.groupby("ISIN")["Dealer"].nunique()
    df_valid = df_full_axes[df_full_axes["AXE_Offer_QTY"] > 0].copy()
    idx = df_valid.groupby("ISIN")["AXE_Offer_YLD"].idxmax()
    df_best = df.loc[idx].copy()
    df_best.rename(columns={"Dealer": "Best_Dealer"}, inplace=True)
    df_best["Nb_Dealers_AXE"] = df_best["ISIN"].map(nb_dealers)
    df_best = df_best[~((df_best["AXE_Offer_QTY"].fillna(0) == 0) & (df_best["Nb_Dealers_AXE"] == 1))]

    return df_full_axes, df_best, last_import

def bucketize_maturity(df):
    df = df.copy()
    df["Maturity"] = pd.to_datetime(df["Maturity"], errors="coerce")

    def maturity_bucket(maturity_date):
        if pd.isna(maturity_date): return "PERP"
        delta = (maturity_date - pd.Timestamp.now()).days / 365
        buckets = [(1, "0-1Y"), (2, "1-2Y"), (3, "2-3Y"), (4, "3-4Y"), (5, "4-5Y"),
                   (7, "5-7Y"), (8, "7-8Y"), (10, "8-10Y"), (15, "10-15Y"),
                   (20, "15-20Y"), (25, "20-25Y"), (30, "25-30Y")]
        for limit, label in buckets:
            if delta <= limit: return label
        return "PERP"

    df["MaturityBucket"] = df["Maturity"].apply(maturity_bucket)
    return df


