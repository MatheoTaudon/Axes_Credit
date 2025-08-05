import pandas as pd

def get_slider_range(series):
    """
    Renvoie une plage min/max réaliste pour un slider Streamlit,
    en tenant compte des valeurs nulles ou constantes.
    """
    vmin, vmax = series.min(), series.max()
    if pd.isnull(vmin) or pd.isnull(vmax) or vmin == vmax:
        return (0.0, 1.0)
    return (float(vmin), float(vmax))
