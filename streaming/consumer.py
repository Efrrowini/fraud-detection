import redis, json, time, joblib, shap
import pandas as pd, numpy as np

import os
r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, decode_responses=True)
QUEUE   = 'txn:queue'
ALERTS  = 'fraud:alerts'
METRICS = 'fraud:metrics'

model     = joblib.load('models/xgb_model.pkl')
threshold = joblib.load('models/threshold.pkl')
explainer = shap.TreeExplainer(model)

FEATURE_COLS = [c for c in
    pd.read_csv('data/processed/test.csv', nrows=0).columns
    if c != 'Class']

total = fraud = 0
print('Consumer running — listening to txn:queue...')

while True:
    item = r.brpop(QUEUE, timeout=1)
    if not item:
        continue

    data = json.loads(item[1])
    txn_id     = data.get('txn_id', '?')
    true_label = int(float(data.get('Class', 0)))

    row = {}
    for col in FEATURE_COLS:
        try: row[col] = float(data[col])
        except: row[col] = 0.0

    X = pd.DataFrame([row])
    proba = float(model.predict_proba(X)[0, 1])
    is_fraud = proba >= threshold

    total += 1
    if is_fraud:
        fraud += 1
        sv = explainer.shap_values(X)[0]
        top3_idx = np.argsort(np.abs(sv))[::-1][:3]
        top3 = [FEATURE_COLS[i] for i in top3_idx]

        alert = json.dumps({
            'txn_id':      txn_id,
            'timestamp':   data.get('timestamp'),
            'score':       round(proba, 4),
            'true_label':  str(true_label),
            'top_factors': top3,
            'amount':      data.get('LogAmount', '?')
        })
        r.lpush(ALERTS, alert)
        r.ltrim(ALERTS, 0, 499)
        print(f'FRAUD DETECTED: {txn_id} | score: {proba:.3f} | factors: {top3}')

    r.hmset(METRICS, {
        'total':       total,
        'fraud':       fraud,
        'fraud_rate':  round(fraud/total*100, 3),
        'last_update': time.time()
    })

    if total % 100 == 0:
        print(f'Processed {total} | Fraud {fraud} ({fraud/total:.2%})')