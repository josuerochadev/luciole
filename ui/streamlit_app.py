"""
pulse_ — Dashboard Monitoring (Streamlit).

Interface dashboard uniquement — le chat est servi par FastAPI (templates HTML).
Direction artistique : éditoriale magazine, alignée sur le design system pulse_.

Lancement :
    # 1) API
    cd fil-rouge && .venv/bin/uvicorn api:app --reload

    # 2) Dashboard
    cd fil-rouge && .venv/bin/streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
import os

API_BASE_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000")
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

st.set_page_config(
    page_title="pulse_ · Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Editorial CSS — pulse_ design system tokens injected into Streamlit
# ---------------------------------------------------------------------------
EDITORIAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap');

    :root {
        --pulse-ink: #1a1a1a;
        --pulse-ink-soft: #2d2d2d;
        --pulse-muted: #6b6b6b;
        --pulse-rule: #d9d6d0;
        --pulse-paper: #faf8f3;
        --pulse-paper-alt: #f2efe8;
        --pulse-white: #ffffff;
        --pulse-accent: #991b1b;
        --pulse-accent-dark: #7f1515;
        --pulse-serif: 'Playfair Display', Georgia, serif;
        --pulse-sans: 'Inter', -apple-system, sans-serif;
        --pulse-mono: 'JetBrains Mono', monospace;
    }

    /* Global overrides */
    .stApp {
        background-color: var(--pulse-paper) !important;
        font-family: var(--pulse-sans) !important;
        color: var(--pulse-ink-soft) !important;
    }

    header[data-testid="stHeader"] {
        background: var(--pulse-paper) !important;
        border-bottom: 3px solid var(--pulse-ink) !important;
    }

    h1, h2, h3 {
        font-family: var(--pulse-serif) !important;
        color: var(--pulse-ink) !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer { visibility: hidden; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--pulse-paper) !important;
        border-right: 1px solid var(--pulse-rule) !important;
    }

    /* Masthead */
    .pulse-masthead-st {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        padding: 24px 0 16px;
        border-bottom: 3px solid var(--pulse-ink);
        margin-bottom: 48px;
        max-width: 100%;
    }
    .pulse-masthead-st .meta {
        font-family: var(--pulse-sans);
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--pulse-muted);
    }
    .pulse-masthead-st .meta:last-child { text-align: right; }
    .pulse-masthead-st .wordmark {
        font-family: var(--pulse-serif);
        font-weight: 900;
        font-size: 28px;
        letter-spacing: -0.02em;
        color: var(--pulse-ink);
        text-decoration: none;
        text-align: center;
    }
    .pulse-masthead-st .wordmark .us {
        color: var(--pulse-accent);
        animation: blink-pulse 2s ease-in-out infinite;
    }
    @keyframes blink-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.15; }
    }

    /* Section headers */
    .ed-section {
        font-family: var(--pulse-sans);
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--pulse-muted);
        padding-bottom: 12px;
        border-bottom: 0.5px solid var(--pulse-rule);
        margin: 48px 0 24px;
    }
    .ed-section-accent {
        font-family: var(--pulse-sans);
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--pulse-accent);
        padding-bottom: 12px;
        border-bottom: 0.5px solid var(--pulse-rule);
        margin: 48px 0 24px;
    }

    /* KPI editorial */
    .ed-kpi {
        padding: 24px 0;
        border-top: 0.5px solid var(--pulse-rule);
    }
    .ed-kpi-label {
        font-family: var(--pulse-sans);
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--pulse-muted);
        margin-bottom: 4px;
    }
    .ed-kpi-value {
        font-family: var(--pulse-serif);
        font-weight: 900;
        font-size: 36px;
        line-height: 1.1;
        color: var(--pulse-ink);
        margin: 8px 0 4px;
    }
    .ed-kpi-sub {
        font-family: var(--pulse-sans);
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--pulse-muted);
    }
    .ed-kpi-trend {
        font-family: var(--pulse-sans);
        font-weight: 500;
        font-size: 13px;
        color: var(--pulse-accent);
        margin-left: 8px;
    }

    /* Health bar */
    .ed-health {
        padding: 20px 0;
        border-top: 0.5px solid var(--pulse-rule);
    }
    .ed-health-row {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .ed-health-label {
        font-family: var(--pulse-sans);
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--pulse-muted);
        min-width: 140px;
    }
    .ed-health-bar {
        flex: 1;
        height: 4px;
        background: var(--pulse-rule);
        border-radius: 0;
        overflow: hidden;
    }
    .ed-health-fill {
        height: 100%;
        transition: width 0.6s ease;
    }
    .ed-health-fill.ok { background: var(--pulse-ink); }
    .ed-health-fill.warn { background: var(--pulse-accent); }
    .ed-health-fill.bad { background: var(--pulse-accent); }
    .ed-health-pct {
        font-family: var(--pulse-serif);
        font-weight: 700;
        font-size: 18px;
        color: var(--pulse-ink);
        min-width: 60px;
        text-align: right;
    }

    /* Nav link */
    .back-link {
        font-family: var(--pulse-sans);
        font-size: 13px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--pulse-ink);
        text-decoration: none;
        border-bottom: 2px solid transparent;
        transition: border-color 0.2s;
    }
    .back-link:hover { border-bottom-color: var(--pulse-accent); }

    /* Footer */
    .ed-footer {
        border-top: 3px solid var(--pulse-ink);
        padding: 24px 0;
        margin-top: 96px;
        text-align: center;
    }
    .ed-footer span {
        font-family: var(--pulse-sans);
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--pulse-muted);
        margin: 0 16px;
    }

    /* Dataframe override */
    .stDataFrame {
        border-radius: 2px !important;
        border: 0.5px solid var(--pulse-rule) !important;
        overflow: hidden;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 2px !important;
        font-family: var(--pulse-sans) !important;
        font-weight: 500;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-size: 11px;
        border: 1px solid var(--pulse-ink) !important;
        background: transparent !important;
        color: var(--pulse-ink) !important;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: var(--pulse-ink) !important;
        color: var(--pulse-paper) !important;
    }

    /* Checkbox */
    .stCheckbox label span {
        font-family: var(--pulse-sans) !important;
        font-size: 13px !important;
    }

    /* Plotly */
    .js-plotly-plot .plotly .modebar { background: transparent !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--pulse-rule); }

    /* Empty state */
    .ed-empty {
        text-align: center;
        padding: 64px 32px;
    }
    .ed-empty h3 {
        font-family: var(--pulse-serif) !important;
        font-weight: 700;
        font-size: 22px;
        color: var(--pulse-ink);
        margin-bottom: 8px;
    }
    .ed-empty p {
        font-family: var(--pulse-sans);
        font-size: 16px;
        color: var(--pulse-muted);
    }
    .ed-empty code {
        font-family: var(--pulse-mono);
        font-size: 13px;
        background: var(--pulse-paper-alt);
        padding: 2px 6px;
        border-radius: 2px;
    }
</style>
"""

st.markdown(EDITORIAL_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers API
# ---------------------------------------------------------------------------
def api_health() -> bool:
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def api_metrics() -> dict | None:
    try:
        r = requests.get(f"{API_BASE_URL}/metrics", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def api_recent(limit: int = 50) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE_URL}/metrics/recent", params={"limit": limit}, timeout=5)
        r.raise_for_status()
        return r.json().get("records", [])
    except requests.RequestException:
        return []


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
def render_kpi(label: str, value: str, sublabel: str = ""):
    st.markdown(
        f'<div class="ed-kpi">'
        f'<div class="ed-kpi-label">{label}</div>'
        f'<div class="ed-kpi-value">{value}</div>'
        f'<div class="ed-kpi-sub">{sublabel}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_health_bar(label: str, value: float, thresholds: tuple[float, float] = (0.0, 0.05)):
    pct = min(value * 100, 100)
    bar_width = 0 if pct == 0 else max(3, pct)

    if value <= thresholds[0]:
        cls = "ok"
    elif value <= thresholds[1]:
        cls = "warn"
    else:
        cls = "bad"

    st.markdown(
        f'<div class="ed-health">'
        f'<div class="ed-health-row">'
        f'<span class="ed-health-label">{label}</span>'
        f'<div class="ed-health-bar"><div class="ed-health-fill {cls}" style="width:{bar_width}%"></div></div>'
        f'<span class="ed-health-pct">{pct:.1f}%</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def plotly_editorial(fig):
    fig.update_layout(
        paper_bgcolor="#faf8f3",
        plot_bgcolor="#faf8f3",
        font=dict(family="Inter, sans-serif", size=11, color="#6b6b6b"),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(
            gridcolor="#d9d6d0",
            zerolinecolor="#d9d6d0",
            showgrid=True,
            tickfont=dict(family="Inter", size=10, color="#6b6b6b"),
        ),
        yaxis=dict(
            gridcolor="#d9d6d0",
            zerolinecolor="#d9d6d0",
            showgrid=True,
            tickfont=dict(family="Inter", size=10, color="#6b6b6b"),
        ),
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#1a1a1a",
            font_size=11,
            font_family="JetBrains Mono, monospace",
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------------------
from datetime import datetime

today = datetime.now().strftime("%A, %B %d, %Y")

st.markdown(
    f'<div class="pulse-masthead-st">'
    f'<span class="meta">Vol. 01 — N°042</span>'
    f'<a href="http://localhost:8000/" class="wordmark">pulse<span class="us">_</span></a>'
    f'<span class="meta">{today}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# Back link
st.markdown(
    '<a href="http://localhost:8000/" class="back-link">&larr; Back to chat</a>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
st.markdown('<div class="ed-section-accent">Dashboard · Monitoring</div>', unsafe_allow_html=True)

col_refresh, col_auto, _ = st.columns([1, 2, 5])
with col_refresh:
    if st.button("Refresh"):
        st.rerun()
with col_auto:
    auto = st.checkbox("Auto-refresh (10s)", value=False)

metrics = api_metrics()

if metrics is None:
    st.markdown(
        '<div class="ed-empty">'
        '<h3>API unavailable</h3>'
        '<p>Start the API with <code>uvicorn api:app --reload</code></p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

if metrics["total_requests"] == 0:
    st.markdown(
        '<div class="ed-empty">'
        '<h3>Awaiting data</h3>'
        '<p>Ask pulse_ a question first.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# --- KPIs ---
st.markdown('<div class="ed-section">Performance</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi("Requests", str(metrics["total_requests"]), "total")
with c2:
    render_kpi("Avg Latency", f'{metrics["avg_duration_ms"]:.0f}ms', "milliseconds")
with c3:
    render_kpi("p95 Latency", f'{metrics["p95_duration_ms"]:.0f}ms', "milliseconds")
with c4:
    render_kpi("Model", metrics.get("model", "gpt-4o-mini"), "OpenAI")

c5, c6, c7, c8 = st.columns(4)
with c5:
    render_kpi("Total Tokens", f'{metrics["total_tokens"]:,}'.replace(",", " "), "consumed")
with c6:
    render_kpi("Tokens / req", f'{metrics["avg_tokens_per_request"]:.0f}', "average")
with c7:
    render_kpi("Total Cost", f'${metrics["total_cost_usd"]:.4f}', "USD")
with c8:
    render_kpi("Cost / req", f'${metrics["avg_cost_per_request_usd"]:.5f}', "USD")

# --- Health ---
st.markdown('<div class="ed-section">Health</div>', unsafe_allow_html=True)

render_health_bar("Error rate", metrics["error_rate"])
render_health_bar("Fallback rate", metrics["fallback_rate"], thresholds=(0.0, 0.10))

# --- Recent requests ---
st.markdown('<div class="ed-section">Recent Queries</div>', unsafe_allow_html=True)

records = api_recent(limit=50)
if records:
    df = pd.DataFrame(records)

    # Latency chart
    if "duration_ms" in df.columns and len(df) > 1:
        st.markdown('<div class="ed-kpi-label" style="margin-bottom:12px;">Latency per query (ms)</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=df["duration_ms"],
            mode="lines",
            fill="tozeroy",
            line=dict(color="#1a1a1a", width=1.5, shape="spline"),
            fillcolor="rgba(26, 26, 26, 0.08)",
            hovertemplate="<b>%{y:.0f} ms</b><extra></extra>",
        ))
        plotly_editorial(fig)
        fig.update_layout(height=200, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "displayModeBar": False})

    # Tokens chart
    if "total_tokens" in df.columns and len(df) > 1:
        st.markdown('<div class="ed-kpi-label" style="margin-top:32px; margin-bottom:12px;">Tokens per query</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=df["total_tokens"],
            marker=dict(color="#991b1b", line_width=0),
            opacity=0.85,
            hovertemplate="<b>%{y:,} tokens</b><extra></extra>",
        ))
        plotly_editorial(fig2)
        fig2.update_layout(height=160, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False, "displayModeBar": False})

    # Table
    st.markdown('<div class="ed-kpi-label" style="margin-top:32px; margin-bottom:12px;">Query log</div>', unsafe_allow_html=True)
    display_cols = [
        c for c in ["timestamp", "question", "duration_ms", "total_tokens", "cost_usd", "fallback", "error"]
        if c in df.columns
    ]
    st.dataframe(df[display_cols].iloc[::-1], use_container_width=True, hide_index=True)

# --- Footer ---
st.markdown(
    '<div class="ed-footer">'
    '<span>pulse_ · AJC Formation · 2026</span>'
    '<span>v1.0.0 · ReAct Agent · gpt-4o-mini</span>'
    '</div>',
    unsafe_allow_html=True,
)

# Auto-refresh
if auto:
    time.sleep(10)
    st.rerun()
