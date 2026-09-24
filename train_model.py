from pathlib import Path
import sys
import json
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.preprocessing import prepare_dataframe, build_preprocessor, NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET

DATA_PATH = ROOT / "data" / "historical_landslides.csv"
MODEL_PATH = ROOT / "ml" / "model.pkl"
METRICS_PATH = ROOT / "ml" / "model_metrics.json"

def train():
    df = pd.read_csv(DATA_PATH)
    df = prepare_dataframe(df, require_target=True)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    if y.nunique() != 2:
        raise ValueError("Training data must contain both landslide classes 0 and 1.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", RandomForestClassifier(
            n_estimators=400,
            max_depth=12,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1
        ))
    ])
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, prob), 4),
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        "test_rows": int(len(y_test)),
        "positive_rate": round(float(y.mean()), 4),
        "dataset_note": "Synthetic demonstration data; metrics are not operational accuracy."
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("Model saved:", MODEL_PATH)
    print("Evaluation:")
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print("WARNING: synthetic demonstration data; validate with authoritative observations before real-world use.")
    return metrics

if __name__ == "__main__":
    train()
