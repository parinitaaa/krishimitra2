from pathlib import Path
import json
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "Crop_recommendation.csv"
ARTIFACT_DIR = HERE / "artifacts"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset missing: {DATA_PATH}\n"
            "Download Crop_recommendation.csv and put it in this folder."
        )

    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()
    missing = sorted(set(FEATURES + [TARGET]) - set(df.columns))
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df = df[FEATURES + [TARGET]].copy()
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[TARGET] = df[TARGET].astype("string").str.strip()
    df = df.dropna().drop_duplicates()
    if df.empty or df[TARGET].nunique() < 2:
        raise ValueError("Not enough valid rows/classes to train.")
    if df[TARGET].value_counts().min() < 2:
        raise ValueError("Each crop class needs at least two rows.")

    X, y = df[FEATURES], df[TARGET].astype(str)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=250,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    report = classification_report(y_test, pred, output_dict=True, zero_division=0)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "features": FEATURES, "classes": model.classes_.tolist()},
        ARTIFACT_DIR / "crop_model.joblib",
    )
    metrics = {
        "rows_after_cleaning": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "number_of_crops": int(y.nunique()),
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_test, pred, labels=model.classes_).tolist(),
        "crop_labels": model.classes_.tolist(),
    }
    (ARTIFACT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Test accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Crop classes: {metrics['number_of_crops']}")
    print(f"Model saved: {ARTIFACT_DIR / 'crop_model.joblib'}")
    print(f"Metrics saved: {ARTIFACT_DIR / 'metrics.json'}")

if __name__ == "__main__":
    main()
