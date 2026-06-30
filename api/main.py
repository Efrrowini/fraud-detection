import joblib, shap, json
import pandas as pd, numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import redis

app = FastAPI(title="Fraud Detection API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"])

model     = joblib.load("models/xgb_model.pkl")
threshold = joblib.load("models/threshold.pkl")
explainer = shap.TreeExplainer(model)
import os
r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, decode_responses=True)

FEATURE_COLS = [c for c in
    pd.read_csv('data/processed/test.csv', nrows=0).columns
    if c != 'Class']


class Transaction(BaseModel):
    features: dict


class FraudResult(BaseModel):
    fraud_probability: float
    is_fraud: bool
    risk_level: str
    top_factors: List[str]
    explanation: str


@app.get("/")
def health():
    return {"status": "online", "model": "XGBoost fraud detector",
            "threshold": round(threshold, 3)}


@app.post("/predict", response_model=FraudResult)
def predict(txn: Transaction):
    row = {col: txn.features.get(col, 0.0) for col in FEATURE_COLS}
    X = pd.DataFrame([row])

    proba = float(model.predict_proba(X)[0, 1])
    is_fraud = proba >= threshold
    risk = 'HIGH'   if proba >= threshold else \
           'MEDIUM' if proba >= threshold*0.6 else 'LOW'

    sv = explainer.shap_values(X)[0]
    top_idx = np.argsort(np.abs(sv))[::-1][:3]
    top_factors = [FEATURE_COLS[i] for i in top_idx]

    explanation = (f"Transaction scored {proba:.1%} fraud probability. "
                   f"Top risk factors: {', '.join(top_factors)}")

    return FraudResult(
        fraud_probability=round(proba, 4),
        is_fraud=is_fraud,
        risk_level=risk,
        top_factors=top_factors,
        explanation=explanation
    )


@app.get("/metrics")
def get_metrics():
    m = r.hgetall('fraud:metrics')
    return m if m else {"total": 0, "fraud": 0, "fraud_rate": 0}


@app.get("/alerts")
def get_alerts(limit: int = 20):
    raw = r.lrange('fraud:alerts', 0, limit-1)
    return [json.loads(a) for a in raw]