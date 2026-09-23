"""Train and use the hybrid (rule-based features + ML) reversal classifier."""
from __future__ import annotations

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

LABEL_NAMES = {0: "none", 1: "bullish_reversal", 2: "bearish_reversal"}


def train_model(X: pd.DataFrame, y: pd.Series, random_state: int = 42):
    """Time-ordered split (no shuffling) to avoid look-ahead leakage,
    then fit a gradient boosting classifier."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    model = GradientBoostingClassifier(random_state=random_state)
    model.fit(X_train, y_train)
    return model, (X_train, X_test, y_train, y_test)


def save_model(model, path: str) -> None:
    joblib.dump(model, path)


def load_model(path: str):
    return joblib.load(path)


def predict_signals(model, X: pd.DataFrame) -> pd.DataFrame:
    """Return predicted label, human-readable signal name, and class
    probabilities for each row of X."""
    proba = model.predict_proba(X)
    preds = model.predict(X)
    out = pd.DataFrame(proba, index=X.index, columns=[f"prob_{LABEL_NAMES[c]}" for c in model.classes_])
    out["signal"] = [LABEL_NAMES[p] for p in preds]
    return out
