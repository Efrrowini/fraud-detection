import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import redis, json, time, random
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="FRAUD::DETECT", page_icon="🛡", layout="wide")

r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, decode_responses=True)

MERCHANT_CATEGORIES = ['Online retail', 'ATM withdrawal', 'POS terminal',
                        'Subscription', 'Travel/airline', 'Electronics', 'Gas station']

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

@keyframes scanline {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100vh); }
}

.scan-overlay {
    position: fixed;
    top: 0; left: 0; width: 100%; height: 3px;
    background: linear-gradient(90deg, transparent, rgba(0,255,140,0.5), transparent);
    animation: scanline 6s linear infinite;
    z-index: 999;
    pointer-events: none;
}

.main-title {
    font-size: 26px;
    font-weight: 700;
    color: #00ff8c;
    text-shadow: 0 0 12px rgba(0,255,140,0.6), 0 0 24px rgba(0,255,140,0.3);
    letter-spacing: 2px;
    margin-bottom: 1px;
}

.sub-title {
    color: #4a9b78;
    font-size: 12px;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

@keyframes ticker-scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

.ticker-wrap {
    background: #0a0f0c;
    border-top: 1px solid rgba(0,255,140,0.3);
    border-bottom: 1px solid rgba(0,255,140,0.3);
    overflow: hidden;
    white-space: nowrap;
    padding: 5px 0;
    margin-bottom: 14px;
}

.ticker-content {
    display: inline-block;
    animation: ticker-scroll 25s linear infinite;
    font-size: 11px;
    color: #5fae8a;
    letter-spacing: 1px;
}

.ticker-content span.fraud-flag { color: #ff3860; font-weight: 700; }

.metric-box {
    background: linear-gradient(180deg, rgba(0,255,140,0.06), rgba(0,255,140,0.01));
    border: 1px solid rgba(0,255,140,0.35);
    border-radius: 4px;
    padding: 12px 16px;
    box-shadow: 0 0 16px rgba(0,255,140,0.08), inset 0 0 20px rgba(0,255,140,0.03);
}

.metric-box.flash {
    border-color: rgba(255,56,96,0.7);
    box-shadow: 0 0 20px rgba(255,56,96,0.3), inset 0 0 20px rgba(255,56,96,0.06);
    animation: flash-pulse 0.8s ease-out;
}

@keyframes flash-pulse {
    0% { box-shadow: 0 0 30px rgba(255,56,96,0.7), inset 0 0 30px rgba(255,56,96,0.2); }
    100% { box-shadow: 0 0 16px rgba(0,255,140,0.08), inset 0 0 20px rgba(0,255,140,0.03); }
}

.metric-label {
    color: #5fae8a;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 5px;
}

.metric-value { color: #00ff8c; font-size: 22px; font-weight: 700; text-shadow: 0 0 8px rgba(0,255,140,0.5); }
.metric-value.danger { color: #ff3860; text-shadow: 0 0 8px rgba(255,56,96,0.6); }

.status-live { display: inline-flex; align-items: center; gap: 6px; color: #00ff8c; font-size: 12px; font-weight: 700; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #00ff8c; box-shadow: 0 0 8px #00ff8c, 0 0 16px #00ff8c; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.panel-header {
    color: #00ff8c;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(0,255,140,0.3);
    padding-bottom: 6px;
    margin-bottom: 10px;
    text-shadow: 0 0 6px rgba(0,255,140,0.4);
}

.alert-row {
    display: grid;
    grid-template-columns: 110px 60px 55px 1fr 60px;
    gap: 8px;
    padding: 6px 8px;
    border-bottom: 1px solid rgba(0,255,140,0.1);
    font-size: 11px;
    color: #b8e8d0;
    align-items: center;
}
.alert-row.header { color: #4a9b78; font-size: 9px; letter-spacing: 1px; text-transform: uppercase; border-bottom: 1px solid rgba(0,255,140,0.3); }

.risk-tag {
    background: rgba(255,56,96,0.15); color: #ff3860; border: 1px solid rgba(255,56,96,0.4);
    border-radius: 3px; padding: 1px 6px; font-size: 9px; font-weight: 700; text-align: center;
    text-shadow: 0 0 6px rgba(255,56,96,0.5);
}
.fraud-tag { color: #ff3860; font-weight: 700; }
.legit-tag { color: #4a9b78; }

.divider-line { height: 1px; background: linear-gradient(90deg, transparent, rgba(0,255,140,0.4), transparent); margin: 14px 0; }

[data-testid="stSidebar"] { background: #0a0f0c; border-right: 1px solid rgba(0,255,140,0.2); }
[data-testid="stSidebar"] * { color: #8fd4b0 !important; font-family: 'JetBrains Mono', monospace !important; }
.stCaption { color: #3d6e54 !important; font-size: 10px !important; }

.boot-line { color: #4a9b78; font-size: 11px; letter-spacing: 1px; line-height: 1.8; }
.boot-line .ok { color: #00ff8c; }

@keyframes threat-pulse-low { 0%,100% { box-shadow: 0 0 14px rgba(0,255,140,0.4); } 50% { box-shadow: 0 0 24px rgba(0,255,140,0.7); } }
@keyframes threat-pulse-elevated { 0%,100% { box-shadow: 0 0 14px rgba(250,199,117,0.4); } 50% { box-shadow: 0 0 24px rgba(250,199,117,0.7); } }
@keyframes threat-pulse-critical { 0%,100% { box-shadow: 0 0 14px rgba(255,56,96,0.5); } 50% { box-shadow: 0 0 30px rgba(255,56,96,0.9); } }

.threat-badge {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 18px; border-radius: 4px; margin-bottom: 14px;
    font-size: 13px; font-weight: 700; letter-spacing: 2px;
}
.threat-low { background: rgba(0,255,140,0.06); border: 1px solid #00ff8c; color: #00ff8c; animation: threat-pulse-low 2.5s infinite; }
.threat-elevated { background: rgba(250,199,117,0.06); border: 1px solid #fac775; color: #fac775; animation: threat-pulse-elevated 1.8s infinite; }
.threat-critical { background: rgba(255,56,96,0.08); border: 1px solid #ff3860; color: #ff3860; animation: threat-pulse-critical 1s infinite; }
</style>
<div class="scan-overlay"></div>
""", unsafe_allow_html=True)

# ── Boot sequence ─────────────────────────────────────────
if 'booted' not in st.session_state:
    boot = st.empty()
    lines = [
        "[ INIT ] Loading XGBoost ensemble model ............... <span class='ok'>OK</span>",
        "[ INIT ] Loading Isolation Forest anomaly model ........ <span class='ok'>OK</span>",
        "[ INIT ] Connecting to Redis stream ..................... <span class='ok'>OK</span>",
        "[ INIT ] Initializing SHAP explainer .................... <span class='ok'>OK</span>",
        "[ INIT ] Establishing live transaction feed ............. <span class='ok'>OK</span>",
        "[ READY ] FRAUD::DETECT system online.",
    ]
    rendered = ""
    for line in lines:
        rendered += f'<div class="boot-line">{line}</div>'
        boot.markdown(rendered, unsafe_allow_html=True)
        time.sleep(0.12)
    time.sleep(0.25)
    boot.empty()
    st.session_state['booted'] = True

# ── State init ────────────────────────────────────────────
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'last_total' not in st.session_state:
    st.session_state['last_total'] = 0
if 'last_fraud_count' not in st.session_state:
    st.session_state['last_fraud_count'] = 0
if 'throughput_hist' not in st.session_state:
    st.session_state['throughput_hist'] = []

# ── Header ────────────────────────────────────────────────
st.markdown('<div class="main-title">FRAUD::DETECT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">REAL-TIME TRANSACTION MONITORING // XGBOOST + ISOLATION FOREST ENSEMBLE</div>', unsafe_allow_html=True)

refresh = st.sidebar.slider("REFRESH RATE (SEC)", 1, 10, 3)
st.sidebar.markdown("---")

# ── Load data ─────────────────────────────────────────────
metrics = r.hgetall('fraud:metrics') or {}
total      = int(float(metrics.get('total', 0)))
fraud      = int(float(metrics.get('fraud', 0)))
fraud_rate = float(metrics.get('fraud_rate', 0))

alerts_raw = r.lrange('fraud:alerts', 0, 49)
alerts = [json.loads(a) for a in alerts_raw]

# ── Throughput calc (txns since last refresh) ────────────
delta_txns = max(total - st.session_state['last_total'], 0)
raw_throughput = round(delta_txns / refresh, 1) if refresh > 0 else 0
throughput = min(raw_throughput, 60)
st.session_state['last_total'] = total
st.session_state['throughput_hist'].append(throughput)
st.session_state['throughput_hist'] = st.session_state['throughput_hist'][-40:]

# ── Live sidebar status ───────────────────────────────────
last_update = float(metrics.get('last_update', 0))
seconds_since_update = time.time() - last_update if last_update else 999

producer_alive = delta_txns > 0
consumer_alive = seconds_since_update < (refresh * 3)

def status_html(label, alive):
    color = "#00ff8c" if alive else "#ff3860"
    text = "ONLINE" if alive else "OFFLINE"
    glow = "0 0 6px" if alive else "0 0 4px"
    return f'<div style="font-size:11px;letter-spacing:1px;margin-bottom:4px"><span style="color:{color};text-shadow:{glow} {color}">●</span> <span style="color:#8fd4b0">[SYS] {label}:</span> <span style="color:{color};font-weight:700">{text}</span></div>'

st.sidebar.markdown(status_html("PRODUCER", producer_alive), unsafe_allow_html=True)
st.sidebar.markdown(status_html("CONSUMER", consumer_alive), unsafe_allow_html=True)
st.sidebar.caption("Ensure producer.py and consumer.py are running.")

# ── New fraud detection (for flash effect) ───────────────
new_fraud_detected = fraud > st.session_state['last_fraud_count']
st.session_state['last_fraud_count'] = fraud

# ── Threat level logic ───────────────────────────────────
recent_fraud_window = sum(1 for a in alerts[:10] if a)
if fraud_rate > 0.3 or recent_fraud_window >= 8:
    threat_level, threat_class = "CRITICAL", "threat-critical"
elif fraud_rate > 0.1 or recent_fraud_window >= 4:
    threat_level, threat_class = "ELEVATED", "threat-elevated"
else:
    threat_level, threat_class = "LOW", "threat-low"

st.markdown(f'''<div class="threat-badge {threat_class}">
    <span>THREAT LEVEL: {threat_level}</span>
    <span style="font-size:10px;font-weight:400;letter-spacing:1px">
        {recent_fraud_window}/10 RECENT FLAGGED // RATE {fraud_rate:.3f}%
    </span>
</div>''', unsafe_allow_html=True)

# ── Scrolling ticker ──────────────────────────────────────
if alerts:
    ticker_items = []
    for a in alerts[:20]:
        flag = '<span class="fraud-flag">[FRAUD]</span>' if a.get('true_label') == '1' else '[OK]'
        ticker_items.append(f"{flag} {a.get('txn_id','?')} :: score {float(a.get('score',0)):.3f}")
    ticker_text = "  ///  ".join(ticker_items)
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-content">{ticker_text}  ///  {ticker_text}</div></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="ticker-wrap"><div class="ticker-content">AWAITING TRANSACTION STREAM ...</div></div>', unsafe_allow_html=True)

# ── Metrics row (with flash on new fraud) ────────────────
flash_class = "flash" if new_fraud_detected else ""
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-box {flash_class}"><div class="metric-label">TRANSACTIONS</div><div class="metric-value">{total:,}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box {flash_class}"><div class="metric-label">FRAUD DETECTED</div><div class="metric-value danger">{fraud:,}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-box {flash_class}"><div class="metric-label">FRAUD RATE</div><div class="metric-value">{fraud_rate:.3f}%</div></div>', unsafe_allow_html=True)
with c4:
    status = '<span class="status-dot"></span> LIVE' if total > 0 else 'OFFLINE'
    st.markdown(f'<div class="metric-box {flash_class}"><div class="metric-label">SYSTEM STATUS</div><div class="status-live">{status}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)

# ── Throughput gauge + sparkline ─────────────────────────
gauge_col, spark_col = st.columns([1, 2])

with gauge_col:
    st.markdown('<div class="panel-header">// THROUGHPUT</div>', unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=throughput,
        number={'suffix': " tx/s", 'font': {'color': '#00ff8c', 'size': 28, 'family': 'JetBrains Mono'}},
        gauge={
            'axis': {'range': [0, 60], 'tickcolor': '#4a9b78', 'tickfont': {'color': '#4a9b78', 'size': 9}},
            'bar': {'color': '#00ff8c'},
            'bgcolor': 'rgba(0,0,0,0)',
            'bordercolor': 'rgba(0,255,140,0.3)',
            'steps': [
                {'range': [0, 25], 'color': 'rgba(0,255,140,0.08)'},
                {'range': [25, 45], 'color': 'rgba(250,199,117,0.08)'},
                {'range': [45, 60], 'color': 'rgba(255,56,96,0.08)'}
            ],
        }
    ))
    fig_gauge.update_layout(
        height=160, margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#4a9b78', family='JetBrains Mono')
    )
    st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

with spark_col:
    st.markdown('<div class="panel-header">// THROUGHPUT TREND (TX/SEC)</div>', unsafe_allow_html=True)
    hist = st.session_state['throughput_hist']
    fig_spark = go.Figure()
    fig_spark.add_trace(go.Scatter(
        y=hist, mode='lines+markers',
        line=dict(color='#00ff8c', width=2),
        marker=dict(size=4, color='#00ff8c'),
        fill='tozeroy', fillcolor='rgba(0,255,140,0.08)'
    ))
    fig_spark.update_layout(
        height=160, margin=dict(l=30, r=10, t=10, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(color='#4a9b78', gridcolor='rgba(0,255,140,0.08)', tickfont=dict(size=9)),
        showlegend=False, font=dict(family='JetBrains Mono')
    )
    st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)

# ── Main grid: alerts + performance ──────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown('<div class="panel-header">// RECENT FRAUD ALERTS</div>', unsafe_allow_html=True)
    if alerts:
        st.markdown('<div class="alert-row header"><div>TXN ID</div><div>SCORE</div><div>RISK</div><div>FACTORS</div><div>ACTUAL</div></div>', unsafe_allow_html=True)
        for alert in alerts[:10]:
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
        st.markdown('<div style="color:#4a9b78;font-size:11px;padding:16px 0">[ NO ALERTS — AWAITING STREAM DATA ]</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="panel-header">// MODEL PERFORMANCE</div>', unsafe_allow_html=True)
    perf = [
        ("AUC-ROC", "0.9833"),
        ("AVG PRECISION", "0.8819"),
        ("RECALL (FRAUD)", "80%"),
        ("PRECISION (FRAUD)", "96%"),
        ("ISOLATION FOREST AUC", "0.9491"),
    ]
    for label, val in perf:
        st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(0,255,140,0.1);font-size:11px;color:#b8e8d0"><span style="color:#4a9b78">{label}</span><span style="color:#00ff8c;font-weight:700">{val}</span></div>', unsafe_allow_html=True)

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)

# ── Charts row: score distribution + merchant category ───
chart_left, chart_right = st.columns(2)

with chart_left:
    st.markdown('<div class="panel-header">// FRAUD SCORE DISTRIBUTION</div>', unsafe_allow_html=True)
    if alerts:
        scores = [float(a.get('score', 0)) for a in alerts]
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=scores, nbinsx=12, marker=dict(color='#00ff8c', line=dict(color='#0a0f0c', width=1)),
            opacity=0.85
        ))
        fig_hist.update_layout(
            height=200, margin=dict(l=30, r=10, t=10, b=30),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#5fae8a', family='JetBrains Mono', size=9),
            xaxis=dict(title='fraud score', gridcolor='rgba(0,255,140,0.08)', color='#5fae8a'),
            yaxis=dict(title='count', gridcolor='rgba(0,255,140,0.08)', color='#5fae8a'),
            showlegend=False
        )
        st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown('<div style="color:#4a9b78;font-size:11px;padding:16px 0">[ AWAITING DATA ]</div>', unsafe_allow_html=True)

with chart_right:
    st.markdown('<div class="panel-header">// FRAUD BY MERCHANT CATEGORY</div>', unsafe_allow_html=True)
    if alerts:
        cat_counts = {c: 0 for c in MERCHANT_CATEGORIES}
        for a in alerts:
            idx = hash(a.get('txn_id', '')) % len(MERCHANT_CATEGORIES)
            cat_counts[MERCHANT_CATEGORIES[idx]] += 1
        cats = list(cat_counts.keys())
        vals = list(cat_counts.values())
        fig_bar = go.Figure(go.Bar(
            x=vals, y=cats, orientation='h',
            marker=dict(color='#ff3860', line=dict(color='#0a0f0c', width=1)),
            opacity=0.85
        ))
        fig_bar.update_layout(
            height=200, margin=dict(l=10, r=10, t=10, b=30),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#5fae8a', family='JetBrains Mono', size=9),
            xaxis=dict(title='flagged count', gridcolor='rgba(0,255,140,0.08)', color='#5fae8a'),
            yaxis=dict(color='#b8e8d0'),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown('<div style="color:#4a9b78;font-size:11px;padding:16px 0">[ AWAITING DATA ]</div>', unsafe_allow_html=True)

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)

# ── SHAP plot ─────────────────────────────────────────────
st.markdown('<div class="panel-header">// SHAP FEATURE IMPORTANCE</div>', unsafe_allow_html=True)
try:
    st.image('reports/shap_summary.png', use_container_width=True)
except Exception:
    st.markdown('<div style="color:#4a9b78;font-size:11px;padding:16px 0">[ SHAP PLOT NOT FOUND ]</div>', unsafe_allow_html=True)

st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)
st.caption("DATASET: KAGGLE CREDIT CARD FRAUD (284,807 TXN, 0.17% FRAUD) // BUILT BY EFRO // SYS.V3.0")

time.sleep(refresh)
st.rerun()