"""Hyperparameter search and decision-threshold tuning for the reversal
classifier. Kept separate from model.py so training/inference code
doesn't need to import sklearn's search/metrics machinery."""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.utils.class_weight import compute_sample_weight


def grid_search_hyperparams(
    X: pd.DataFrame, y: pd.Series, param_grid: dict, n_splits: int = 3,
    search_n_estimators: int = 150, random_state: int = 42,
) -> tuple[dict, float]:
    """Time-series cross-validated grid search, scored by macro-F1 over
    the two reversal classes only (class 0 / "none" dominates the data
    and isn't what we're optimizing for). Returns (best_params, best_score).
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    keys = list(param_grid.keys())
    best_score, best_params = -1.0, {}

    for combo in product(*param_grid.values()):
        params = dict(zip(keys, combo))
        fold_scores = []
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            sample_weight = compute_sample_weight("balanced", y_tr)
            model = GradientBoostingClassifier(
                random_state=random_state, n_estimators=search_n_estimators, **params
            )
            model.fit(X_tr, y_tr, sample_weight=sample_weight)
            y_pred = model.predict(X_val)
            fold_scores.append(f1_score(y_val, y_pred, labels=[1, 2], average="macro", zero_division=0))
        avg_score = float(np.mean(fold_scores))
        if avg_score > best_score:
            best_score, best_params = avg_score, params

    return best_params, best_score


def tune_thresholds(y_true: np.ndarray, proba: np.ndarray, classes, grid: np.ndarray | None = None) -> dict:
    """Independently tune a probability threshold per reversal class
    (1=bullish, 2=bearish) to maximize that class's F1 on a validation
    set. Returns {class: threshold}."""
    if grid is None:
        grid = np.arange(0.3, 0.91, 0.05)
    classes = list(classes)
    thresholds = {}
    for cls in (1, 2):
        idx = classes.index(cls)
        y_bin = (y_true == cls).astype(int)
        best_t, best_f1 = 0.5, -1.0
        for t in grid:
            pred_bin = (proba[:, idx] >= t).astype(int)
            f1 = f1_score(y_bin, pred_bin, zero_division=0)
            if f1 > best_f1:
                best_f1, best_t = f1, t
        thresholds[cls] = float(best_t)
    return thresholds


def predict_with_thresholds(proba: np.ndarray, classes, thresholds: dict) -> np.ndarray:
    """Predict whichever reversal class exceeds its own tuned threshold
    with the highest probability; 'none' (class 0) otherwise. This lets
    each class's alert sensitivity be tuned independently, instead of
    always taking the raw argmax."""
    classes = list(classes)
    preds = np.zeros(len(proba), dtype=int)
    for i, row in enumerate(proba):
        best_cls, best_p = 0, 0.0
        for cls, t in thresholds.items():
            p = row[classes.index(cls)]
            if p >= t and p > best_p:
                best_p, best_cls = p, cls
        preds[i] = best_cls
    return preds
