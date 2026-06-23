import numpy as np
import joblib
import pandas as pd


def ensemble_score(X: pd.DataFrame,
                   xgb_weight: float = 0.7,
                   iso_weight: float = 0.3) -> np.ndarray:
    """Weighted average of XGBoost probability and Isolation Forest anomaly score."""
    xgb = joblib.load('models/xgb_model.pkl')
    iso = joblib.load('models/isolation_forest.pkl')

    xgb_prob = xgb.predict_proba(X)[:, 1]

    iso_scores = -iso.score_samples(X)
    iso_norm = (iso_scores - iso_scores.min()) / (
        iso_scores.max() - iso_scores.min() + 1e-8)

    combined = xgb_weight * xgb_prob + iso_weight * iso_norm
    return combined


def predict_single(transaction: dict) -> dict:
    """Score a single transaction dict. Returns score + risk level."""
    xgb = joblib.load('models/xgb_model.pkl')
    iso = joblib.load('models/isolation_forest.pkl')
    threshold = joblib.load('models/threshold.pkl')

    X = pd.DataFrame([transaction])
    xgb_prob = float(xgb.predict_proba(X)[0, 1])
    iso_score = float(-iso.score_samples(X)[0])

    combined = 0.7 * xgb_prob + 0.3 * iso_score

    return {
        'xgb_score':      round(xgb_prob, 4),
        'iso_score':      round(iso_score, 4),
        'ensemble_score': round(combined, 4),
        'is_fraud':       xgb_prob >= threshold,
        'risk_level':     'HIGH'   if xgb_prob >= threshold else
                          'MEDIUM' if xgb_prob >= threshold*0.7 else 'LOW'
    }