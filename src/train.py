import pandas as pd
import numpy as np
import joblib, mlflow, mlflow.sklearn
from xgboost import XGBClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    classification_report, precision_recall_curve
)

FEATURE_COLS = [c for c in pd.read_csv('data/processed/train.csv',
                nrows=0).columns if c != 'Class']


def train():
    train = pd.read_csv('data/processed/train.csv')
    test  = pd.read_csv('data/processed/test.csv')

    X_train, y_train = train[FEATURE_COLS], train['Class']
    X_test,  y_test  = test[FEATURE_COLS],  test['Class']

    mlflow.set_experiment('fraud-detection')
    with mlflow.start_run(run_name='xgboost-smote'):

        model = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=1,
            eval_metric='aucpr',
            random_state=42,
            verbosity=0
        )
        print('Training XGBoost...')
        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],
                  verbose=False)

        proba = model.predict_proba(X_test)[:, 1]

        # Find optimal threshold
        prec, rec, thresholds = precision_recall_curve(y_test, proba)
        f1_scores = 2 * (prec * rec) / (prec + rec + 1e-8)
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx]
        y_pred = (proba >= best_threshold).astype(int)

        auc = roc_auc_score(y_test, proba)
        ap  = average_precision_score(y_test, proba)

        mlflow.log_params({'n_estimators': 500, 'max_depth': 6,
                           'threshold': round(best_threshold, 3)})
        mlflow.log_metrics({'auc_roc': auc, 'avg_precision': ap})
        mlflow.sklearn.log_model(model, 'model')

        print(f'\n{"="*45}')
        print(f'  AUC-ROC         : {auc:.4f}')
        print(f'  Avg Precision   : {ap:.4f}')
        print(f'  Best threshold  : {best_threshold:.3f}')
        print(f'{"="*45}')
        print(classification_report(y_test, y_pred,
              target_names=['Legit', 'Fraud']))

    joblib.dump(model, 'models/xgb_model.pkl')
    joblib.dump(best_threshold, 'models/threshold.pkl')
    print('Saved -> models/xgb_model.pkl')
    return model, best_threshold


if __name__ == '__main__':
    train()