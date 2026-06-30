import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import redis, json, time
import pandas as pd

st.set_page_config(page_title="FRAUD::DETECT", page_icon="🛡", layout="wide")

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# ── Sci-fi CSS injection ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace !important;
}

.stApp {
    background: #060a08;
    background-image:
        linear-gradient(rgba(0,255,140,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,140,0.02) 1px, transparent 1px);
    background-size: 24px 24px;
}

.main-title {
    font-size: 28px;
    font-weight: 700;
    color: #00ff8c;
    text-shadow: 0 0 12px rgba(0,255,140,0.6), 0 0 24px rgba(0,255,140,0.3);
    letter-spacing: 2px;
    margin-bottom: 2px;
}

.sub-title {
    color: #4a9b78;
    font-size: 13px;
    letter-spacing: 1px;
    margin-bottom: 24px;
}

.metric-box {
    background: linear-gradient(180deg, rgba(0,255,140,0.06), rgba(0,255,140,0.01));
    border: 1px solid rgba(0,255,140,0.35);
    border-radius: 4px;
    padding: 16px 18px;
    box-shadow: 0 0 16px rgba(0,255,140,0.08), inset 0 0 20px rgba(0,255,140,0.03);
}

.metric-label {
    color: #5fae8a;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.metric-value {
    color: #00ff8c;
    font-size: 26px;
    font-weight: 700;
    text-shadow: 0 0 8px rgba(0,255,140,0.5);
}

.metric-value.danger {
    color: #ff3860;
    text-shadow: 0 0 8px rgba(255,56,96,0.6);
}

.status-live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #00ff8c;
    font-size: 13px;
    font-weight: 700;
}

.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00ff8c;
    box-shadow: 0 0 8px #00ff8c, 0 0 16px #00ff8c;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

.panel-header {
    color: #00ff8c;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(0,255,140,0.3);
    padding-bottom: 8px;
    margin-bottom: 12px;
    text-shadow: 0 0 6px rgba(0,255,140,0.4);
}

.alert-row {
    display: grid;
    grid-template-columns: 120px 70px 60px 1fr 70px;
    gap: 10px;
    padding: 8px 10px;
    border-bottom: 1px solid rgba(0,255,140,0.1);
    font-size: 12px;
    color: #b8e8d0;
    align-items: center;
}

.alert-row.header {
    color: #4a9b78;
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(0,255,140,0.3);
}

.risk-tag {
    background: rgba(255,56,96,0.15);
    color: #ff3860;
    border: 1px solid rgba(255,56,96,0.4);
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
    text-align: center;
    text-shadow: 0 0 6px rgba(255,56,96,0.5);
}

.fraud-tag {
    color: #ff3860;
    font-weight: 700;
}

.legit-tag {
    color: #4a9b78;
}

.divider-line {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,255,140,0.4), transparent);
    margin: 20px 0;
}

[data-testid="stSidebar"] {
    background: #0a0f0c;
    border-right: 1px solid rgba(0,255,140,0.2);
}

[data-testid="stSidebar"] * {
    color: #8fd4b0 !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.stCaption {
    color: #3d6e54 !important;
    font-size: 11px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────
st.markdown('<div class="main-title">FRAUD::DETECT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">REAL-TIME TRANSACTION MONITORING // XGBOOST + ISOLATION FOREST ENSEMBLE</div>', unsafe_allow_html=True)

refresh = st.sidebar.slider("REFRESH RATE (SEC)", 1, 10, 3)
st.sidebar.markdown("---")
st.sidebar.markdown("**[SYS] PRODUCER STATUS**")
st.sidebar.markdown("**[SYS] CONSUMER STATUS**")
st.sidebar.caption("Ensure producer.py and consumer.py are running.")

# ── Metrics ───────────────────────────────────────────────
metrics = r.hgetall('fraud:metrics') or {}
total      = int(float(metrics.get('total', 0)))
fraud      = int(float(metrics.get('fraud', 0)))
fraud_rate = float(metrics.get('fraud_rate', 0))

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-box"><div class="metric-label">TRANSACTIONS</div><div class="metric-value">{total:,}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box"><div class="metric-label">FRAUD DETECTED</div><div class="metric-value danger">{fraud:,}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-box"><div class="metric-label">FRAUD RATE</div><div class="metric-value">{fraud_rate:.3f}%</div></div>', unsafe_allow_html=True)
with c4:
    status = '<span class="status-dot"></span> LIVE' if total > 0 else 'OFFLINE'
    st.markdown(f'<div class="metric-box"><div class="metric-label">SYSTEM STATUS</div><div class="status-live">{status}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown('<div class="panel-header">// RECENT FRAUD ALERTS</div>', unsafe_allow_html=True)
    alerts_raw = r.lrange('fraud:alerts', 0, 14)
    if alerts_raw:
        st.markdown('<div class="alert-row header"><div>TXN ID</div><div>SCORE</div><div>RISK</div><div>FACTORS</div><div>ACTUAL</div></div>', unsafe_allow_html=True)
        for a in alerts_raw:
            alert = json.loads(a)
            factors = alert.get('top_factors', [])
            score = float(alert.get('score', 0))
            actual = alert.get('true_label')
            actual_html = '<span class="fraud-tag">FRAUD</span>' if actual == '1' else '<span class="legit-tag">LEGIT</span>'
            st.markdown(f'''<div class="alert-row">
                <div>{alert.get('txn_id','?')}</div>
                <div>{score:.3f}</div>
                <div><span class="risk-tag">HIGH</span></div>
                <div>{', '.join(factors[:2])}</div>
                <div>{actual_html}</div>
            </div>''', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#4a9b78;font-size:12px;padding:20px 0">[ NO ALERTS — AWAITING STREAM DATA ]</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="panel-header">// MODEL PERFORMANCE</div>', unsafe_allow_html=True)
    perf = [
        ("AUC-ROC", "0.9833"),
        ("AVG PRECISION", "0.8819"),
        ("RECALL (FRAUD)", "80%"),
        ("PRECISION (FRAUD)", "96%"),
    ]
    for label, val in perf:
        st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(0,255,140,0.1);font-size:12px;color:#b8e8d0"><span style="color:#4a9b78">{label}</span><span style="color:#00ff8c;font-weight:700">{val}</span></div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
    try:
        st.image('reports/shap_summary.png', use_container_width=True)
    except Exception:
        pass

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)
st.caption("DATASET: KAGGLE CREDIT CARD FRAUD (284,807 TXN, 0.17% FRAUD) // BUILT BY EFRO // SYS.V1.0")

time.sleep(refresh)
st.rerun()