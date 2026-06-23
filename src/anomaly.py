import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score


def train_isolation_forest():
    # Train ONLY on legit transactions — learns what "normal" looks like
    train = pd.read_csv('data/processed/train.csv')
    test  = pd.read_csv('data/processed/test.csv')

    FEATURE_COLS = [c for c in train.columns if c != 'Class']

    # Only legit for training — unsupervised!
    X_legit = train[train['Class']==0][FEATURE_COLS]
    X_test  = test[FEATURE_COLS]
    y_test  = test['Class']

    print('Training Isolation Forest on legit transactions...')
    iso = IsolationForest(
        n_estimators=200,
        contamination=0.001,
        random_state=42,
        n_jobs=-1
    )
    iso.fit(X_legit)

    # Anomaly scores — more negative = more anomalous
    scores = -iso.score_samples(X_test)
    # Normalise to [0,1]
    scores = (scores - scores.min()) / (scores.max() - scores.min())

    auc = roc_auc_score(y_test, scores)
    print(f'Isolation Forest AUC-ROC: {auc:.4f}')

    joblib.dump(iso, 'models/isolation_forest.pkl')
    print('Saved -> models/isolation_forest.pkl')
    return iso


if __name__ == '__main__':
    train_isolation_forest()