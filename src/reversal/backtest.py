"""Evaluate a trained reversal model: classification metrics plus a
lead-time check (how many bars ahead of the actual pivot the model's
signal first fires)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

from .model import LABEL_NAMES


def evaluate(model, X_test: pd.DataFrame, y_test: pd.Series) -> str:
    y_pred = model.predict(X_test)
    report = classification_report(
        y_test, y_pred, target_names=[LABEL_NAMES[c] for c in sorted(LABEL_NAMES)], zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=sorted(LABEL_NAMES))
    cm_str = pd.DataFrame(
        cm, index=[f"true_{LABEL_NAMES[c]}" for c in sorted(LABEL_NAMES)],
        columns=[f"pred_{LABEL_NAMES[c]}" for c in sorted(LABEL_NAMES)]
    ).to_string()
    return f"{report}\n\nConfusion matrix:\n{cm_str}"


def average_lead_time(y_true: pd.Series, y_pred: np.ndarray, target_class: int, max_gap: int = 20) -> float | None:
    """For each true pivot event of `target_class`, find the nearest
    preceding bar where the model predicted that class, and average the
    gap in bars. Returns None if there are no matches."""
    true_arr = y_true.to_numpy()
    pred_arr = np.asarray(y_pred)
    event_idxs = np.where(true_arr == target_class)[0]
    gaps = []
    for idx in event_idxs:
        window_start = max(0, idx - max_gap)
        window_preds = pred_arr[window_start:idx + 1]
        hits = np.where(window_preds == target_class)[0]
        if len(hits) > 0:
            first_hit_idx = window_start + hits[0]
            gaps.append(idx - first_hit_idx)
    if not gaps:
        return None
    return float(np.mean(gaps))
