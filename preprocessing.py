import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from services.feature_engineering import NUMERIC_FEATURES, CATEGORICAL_FEATURES, engineer_features

TARGET = "landslide"

REQUIRED_COLUMNS = {
    "rainfall_1h", "rainfall_3h", "rainfall_24h", "soil_moisture",
    "temperature", "humidity", "elevation", "slope", "aspect",
    "land_cover", "historical_landslide_density", TARGET,
}

def prepare_dataframe(df, require_target=False):
    """Validate, clean and engineer the model dataframe."""
    df = df.copy()
    needed = REQUIRED_COLUMNS if require_target else REQUIRED_COLUMNS - {TARGET}
    missing = sorted(needed - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    if require_target and TARGET not in df.columns:
        raise ValueError("Training data must contain the 'landslide' target column.")

    numeric = [c for c in REQUIRED_COLUMNS if c not in {"land_cover", TARGET}]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["land_cover"] = df["land_cover"].astype("string")
    if TARGET in df:
        df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")

    df = df.dropna(subset=list(needed))
    if require_target:
        df = df[df[TARGET].isin([0, 1])]
        df[TARGET] = df[TARGET].astype(int)

    engineered = pd.DataFrame(
        [engineer_features(r.to_dict()) for _, r in df.iterrows()]
    )
    return engineered.reset_index(drop=True)

def build_preprocessor():
    return ColumnTransformer([
        ("num", "passthrough", NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
