import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import redis, json, time
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Fraud Detection Dashboard",
                   page_icon="🛡", layout="wide")

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

st.title("🛡 Real-time Fraud Detection Dashboard")
st.markdown("_Live transaction monitoring — XGBoost + Isolation Forest ensemble_")

refresh = st.sidebar.slider("Refresh interval (sec)", 1, 10, 3)
st.sidebar.info("Make sure producer.py and consumer.py are running in separate terminals.")

# Live metrics
metrics = r.hgetall('fraud:metrics') or {}
total      = int(float(metrics.get('total', 0)))
fraud      = int(float(metrics.get('fraud', 0)))
fraud_rate = float(metrics.get('fraud_rate', 0))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total transactions", f"{total:,}")
col2.metric("Fraud detected", f"{fraud:,}")
col3.metric("Fraud rate", f"{fraud_rate:.3f}%")
col4.metric("Status", "🟢 Live" if total > 0 else "🔴 No data")

st.divider()

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Recent fraud alerts")
    alerts_raw = r.lrange('fraud:alerts', 0, 14)
    if alerts_raw:
        rows = []
        for a in alerts_raw:
            alert = json.loads(a)
            factors = alert.get('top_factors', [])
            rows.append({
                'Transaction ID': alert.get('txn_id', '?'),
                'Score': float(alert.get('score', 0)),
                'Risk': 'HIGH' if float(alert.get('score', 0)) > 0.7 else 'MEDIUM',
                'Top factors': ', '.join(factors[:2]),
                'Actual': 'Fraud' if alert.get('true_label') == '1' else 'Legit'
            })
        alerts_df = pd.DataFrame(rows)
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts yet — start producer.py and consumer.py")

with col_right:
    st.subheader("Model performance")
    perf = pd.DataFrame({
        'Metric': ['AUC-ROC', 'Avg Precision', 'Recall (fraud)', 'Precision (fraud)'],
        'Value':  ['0.9833', '0.8819', '80%', '96%']
    })
    st.dataframe(perf, use_container_width=True, hide_index=True)
    try:
        st.image('reports/shap_summary.png',
                 caption='SHAP feature importance', use_container_width=True)
    except Exception:
        st.warning("SHAP plot not found")

st.divider()
st.caption("Dataset: Kaggle Credit Card Fraud (284,807 txns, 0.17% fraud) | Built by Efro")
time.sleep(refresh)
st.rerun()