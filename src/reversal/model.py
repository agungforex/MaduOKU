"""Train and use the hybrid (rule-based features + ML) reversal classifier."""
from __future__ import annotations

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight

from .tuning import predict_with_thresholds

LABEL_NAMES = {0: "none", 1: "bullish_reversal", 2: "bearish_reversal"}

DEFAULT_PARAMS = dict(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8)


def time_ordered_splits(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, val_size: float = 0.15):
    """Split chronologically into train / validation / test (no
    shuffling, so no look-ahead leakage). Validation is used to tune
    decision thresholds; test is only touched for final evaluation."""
    n = len(X)
    test_n = int(n * test_size)
    val_n = int(n * val_size)
    train_n = n - test_n - val_n
    X_train, y_train = X.iloc[:train_n], y.iloc[:train_n]
    X_val, y_val = X.iloc[train_n:train_n + val_n], y.iloc[train_n:train_n + val_n]
    X_test, y_test = X.iloc[train_n + val_n:], y.iloc[train_n + val_n:]
    return X_train, X_val, X_test, y_train, y_val, y_test


def train_model(X: pd.DataFrame, y: pd.Series, params: dict | None = None, random_state: int = 42):
    """Fit a gradient boosting classifier with class-balanced sample
    weights (reversal bars are a small minority of the data -- without
    balancing, the model just predicts "none" everywhere)."""
    params = {**DEFAULT_PARAMS, **(params or {})}
    sample_weight = compute_sample_weight(class_weight="balanced", y=y)
    model = GradientBoostingClassifier(random_state=random_state, **params)
    model.fit(X, y, sample_weight=sample_weight)
    return model


def save_model(bundle, path: str) -> None:
    """`bundle` is typically {"model": ..., "thresholds": ..., "params": ...}."""
    joblib.dump(bundle, path)


def load_model(path: str):
    return joblib.load(path)


def predict_signals(model, X: pd.DataFrame, thresholds: dict | None = None) -> pd.DataFrame:
    """Return predicted label, human-readable signal name, and class
    probabilities for each row of X. If `thresholds` (from
    tuning.tune_thresholds) is given, use those instead of raw argmax."""
    proba = model.predict_proba(X)
    if thresholds:
        preds = predict_with_thresholds(proba, model.classes_, thresholds)
    else:
        preds = model.predict(X)
    out = pd.DataFrame(proba, index=X.index, columns=[f"prob_{LABEL_NAMES[c]}" for c in model.classes_])
    out["signal"] = [LABEL_NAMES[p] for p in preds]
    return out
