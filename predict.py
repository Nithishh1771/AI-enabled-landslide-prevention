from pathlib import Path
import joblib
import pandas as pd
from config import Config
from ml.preprocessing import prepare_dataframe, NUMERIC_FEATURES, CATEGORICAL_FEATURES

MODEL_PATH = Config.MODEL_PATH

def predict_risk_probability(reading):
    """Return the model probability for landslide class 1."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError("model.pkl not found. Run: python ml/train_model.py")
    model = joblib.load(MODEL_PATH)
    df = prepare_dataframe(pd.DataFrame([reading]), require_target=False)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    return float(model.predict_proba(X)[0, 1])
