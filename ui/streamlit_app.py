"""
Pulse — Agent de veille technologique.

Interface utilisateur Streamlit consommant l'API FastAPI (api.py) :
- POST /ask           : envoi d'une requête
- GET  /health        : healthcheck
- GET  /metrics       : agrégats de monitoring (M5E5)
- GET  /metrics/recent: dernières requêtes

Lancement :
    # 1) Démarrer l'API
    cd fil-rouge && source .venv/bin/activate && uvicorn api:app --reload

    # 2) Démarrer l'UI
    cd fil-rouge && source .venv/bin/activate && streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import base64
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000")
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

REQUEST_TIMEOUT = 120

st.set_page_config(
    page_title="Pulse · Veille Tech",
    page_icon=(ASSETS_DIR / "icon.svg").as_posix(),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Brand tokens
# ---------------------------------------------------------------------------
BRAND = {
    "name": "Pulse",
    "tagline": "Veille Tech Agent",
    "version": "2.0",
}

COLORS = {
    # Backgrounds
    "bg_deep": "#0B0B10",
    "bg_primary": "#0F1118",
    "bg_elevated": "#161922",
    "bg_card_solid": "#1A1D28",
    # Glass
    "glass_bg": "rgba(255, 255, 255, 0.03)",
    "glass_border": "rgba(255, 255, 255, 0.06)",
    "glass_hover": "rgba(255, 255, 255, 0.10)",
    # Brand colors
    "brand_blue": "#3B82F6",
    "brand_indigo": "#818CF8",
    "brand_cyan": "#22D3EE",
    "brand_gradient": "linear-gradient(135deg, #3B82F6, #818CF8)",
    "brand_glow": "rgba(59, 130, 246, 0.12)",
    "brand_glow_strong": "rgba(59, 130, 246, 0.25)",
    # Semantic
    "success": "#10B981",
    "success_glow": "rgba(16, 185, 129, 0.12)",
    "warning": "#F59E0B",
    "warning_glow": "rgba(245, 158, 11, 0.12)",
    "danger": "#EF4444",
    "danger_glow": "rgba(239, 68, 68, 0.12)",
    # Text
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#4B5563",
    # Misc
    "border": "rgba(255, 255, 255, 0.06)",
    "border_hover": "rgba(255, 255, 255, 0.12)",
}


# ---------------------------------------------------------------------------
# Logo helper
# ---------------------------------------------------------------------------
def get_logo_b64() -> str:
    """Encode le logo SVG en base64 pour l'afficher inline."""
    logo_path = ASSETS_DIR / "logo.svg"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


LOGO_B64 = get_logo_b64()


# ---------------------------------------------------------------------------
# Custom CSS — Pulse Brand Identity
# ---------------------------------------------------------------------------
CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap');

    /* --- Accessibility --- */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }}
    }}

    /* --- Global --- */
    .stApp {{
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background: {COLORS['bg_deep']};
    }}

    h1, h2, h3 {{
        font-family: 'Space Grotesk', sans-serif !important;
    }}

    /* --- Ambient blobs --- */
    .ambient-glow {{
        position: fixed;
        border-radius: 50%;
        filter: blur(100px);
        opacity: 0.05;
        pointer-events: none;
        z-index: 0;
    }}
    .ambient-glow.a {{
        width: 500px; height: 500px;
        background: {COLORS['brand_blue']};
        top: 5%; right: 10%;
        animation: drift-a 25s ease-in-out infinite alternate;
    }}
    .ambient-glow.b {{
        width: 350px; height: 350px;
        background: {COLORS['brand_indigo']};
        bottom: 15%; left: 5%;
        animation: drift-a 30s ease-in-out infinite alternate-reverse;
    }}
    .ambient-glow.c {{
        width: 250px; height: 250px;
        background: {COLORS['brand_cyan']};
        top: 50%; left: 40%;
        animation: drift-a 20s ease-in-out infinite alternate;
    }}
    @keyframes drift-a {{
        0% {{ transform: translate(0, 0); }}
        100% {{ transform: translate(40px, -30px); }}
    }}

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(11, 11, 16, 0.97) 0%, rgba(8, 8, 12, 0.99) 100%) !important;
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-right: 1px solid {COLORS['glass_border']};
    }}

    .sidebar-logo {{
        padding: 0.5rem 0 1rem 0;
    }}

    .sidebar-logo img {{
        height: 42px;
        width: auto;
    }}

    /* --- Status badge --- */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        font-family: 'Fira Code', monospace;
        backdrop-filter: blur(10px);
    }}

    .status-online {{
        background: {COLORS['success_glow']};
        color: {COLORS['success']};
        border: 1px solid rgba(16, 185, 129, 0.2);
    }}

    .status-online .pulse-dot {{
        width: 8px; height: 8px;
        border-radius: 50%;
        background: {COLORS['success']};
        position: relative;
    }}

    .status-online .pulse-dot::before {{
        content: '';
        position: absolute;
        inset: -4px;
        border-radius: 50%;
        border: 1.5px solid {COLORS['success']};
        animation: pulse-ring 2s ease-out infinite;
    }}

    @keyframes pulse-ring {{
        0% {{ opacity: 0.8; transform: scale(1); }}
        100% {{ opacity: 0; transform: scale(2.2); }}
    }}

    .status-offline {{
        background: {COLORS['danger_glow']};
        color: {COLORS['danger']};
        border: 1px solid rgba(239, 68, 68, 0.2);
    }}

    /* --- Section headers --- */
    .section-header {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: {COLORS['text_muted']};
        margin: 1.75rem 0 0.75rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {COLORS['glass_border']};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .section-dot {{
        width: 5px; height: 5px;
        border-radius: 50%;
        background: {COLORS['brand_gradient']};
    }}

    /* --- Glass cards --- */
    .glass-card, .kpi-card {{
        background: {COLORS['glass_bg']};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {COLORS['glass_border']};
        border-radius: 16px;
        padding: 1.25rem;
        position: relative;
        overflow: hidden;
        transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1),
                    border-color 0.25s ease,
                    box-shadow 0.25s ease;
    }}

    .kpi-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: {COLORS['brand_gradient']};
        opacity: 0;
        transition: opacity 0.25s ease;
    }}

    .kpi-card:hover {{
        transform: translateY(-3px);
        border-color: {COLORS['border_hover']};
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    }}

    .kpi-card:hover::before {{ opacity: 1; }}

    .kpi-icon {{
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        opacity: 0.6;
    }}

    .kpi-label {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    .kpi-value {{
        font-family: 'Fira Code', monospace;
        font-size: 1.6rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
        margin: 0.3rem 0 0.1rem 0;
        line-height: 1.2;
    }}

    .kpi-sublabel {{
        font-family: 'Fira Code', monospace;
        font-size: 0.68rem;
        color: {COLORS['text_muted']};
    }}

    /* --- Health gauge --- */
    .health-gauge {{
        background: {COLORS['glass_bg']};
        backdrop-filter: blur(12px);
        border: 1px solid {COLORS['glass_border']};
        border-radius: 16px;
        padding: 1.25rem;
    }}

    .gauge-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }}

    .gauge-label {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.78rem;
        font-weight: 500;
        color: {COLORS['text_secondary']};
    }}

    .gauge-value {{
        font-family: 'Fira Code', monospace;
        font-size: 0.85rem;
        font-weight: 600;
    }}

    .gauge-bar {{
        width: 100%; height: 6px;
        background: rgba(255, 255, 255, 0.04);
        border-radius: 3px;
        overflow: hidden;
    }}

    .gauge-fill {{
        height: 100%;
        border-radius: 3px;
        transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .gauge-fill::after {{
        content: '';
        display: block;
        width: 100%; height: 100%;
        border-radius: 3px;
        animation: shimmer 2.5s ease-in-out infinite;
        background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.12) 50%, transparent 100%);
    }}

    @keyframes shimmer {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(100%); }}
    }}

    .gauge-good {{ background: linear-gradient(90deg, {COLORS['success']}, #34D399); }}
    .gauge-warn {{ background: linear-gradient(90deg, {COLORS['warning']}, #FBBF24); }}
    .gauge-bad {{ background: linear-gradient(90deg, {COLORS['danger']}, #F87171); }}

    .text-good {{ color: {COLORS['success']}; }}
    .text-warn {{ color: {COLORS['warning']}; }}
    .text-bad {{ color: {COLORS['danger']}; }}

    /* --- Chat messages --- */
    .stChatMessage {{
        border-radius: 16px;
        border: 1px solid {COLORS['glass_border']};
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        backdrop-filter: blur(8px);
        transition: border-color 0.2s ease;
        animation: msg-enter 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
    }}

    @keyframes msg-enter {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .stChatMessage:hover {{
        border-color: {COLORS['border_hover']};
    }}

    /* --- Typing indicator --- */
    .typing-indicator {{
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 14px 18px;
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        border-radius: 16px;
        width: fit-content;
    }}

    @keyframes typing-dot {{
        0%, 60%, 100% {{ opacity: 0.15; transform: translateY(0) scale(1); }}
        30% {{ opacity: 1; transform: translateY(-5px) scale(1.15); }}
    }}

    .typing-indicator span.dot {{
        width: 7px; height: 7px;
        border-radius: 50%;
        background: {COLORS['brand_blue']};
        animation: typing-dot 1.4s cubic-bezier(0.16, 1, 0.3, 1) infinite;
    }}

    .typing-indicator span.dot:nth-child(2) {{ animation-delay: 0.15s; }}
    .typing-indicator span.dot:nth-child(3) {{ animation-delay: 0.3s; }}

    .typing-label {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.73rem;
        color: {COLORS['text_muted']};
        margin-left: 10px;
        font-style: italic;
    }}

    /* --- Chat input --- */
    .stChatInput textarea {{
        font-family: 'DM Sans', sans-serif !important;
        border-radius: 16px !important;
    }}

    /* --- Welcome card --- */
    .welcome-card {{
        background: linear-gradient(135deg, {COLORS['brand_glow']}, rgba(129, 140, 248, 0.05), transparent);
        border: 1px solid {COLORS['glass_border']};
        border-radius: 24px;
        padding: 3rem 2rem;
        margin: 1.5rem 0 2rem 0;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}

    .welcome-card::before {{
        content: '';
        position: absolute;
        top: -60%; left: -30%;
        width: 160%; height: 160%;
        background: radial-gradient(ellipse at 40% 50%, {COLORS['brand_glow']}, transparent 60%);
        animation: welcome-glow 10s ease-in-out infinite alternate;
        pointer-events: none;
    }}

    @keyframes welcome-glow {{
        0% {{ transform: translate(0, 0) rotate(0deg); }}
        100% {{ transform: translate(3%, 2%) rotate(3deg); }}
    }}

    .welcome-logo {{
        margin-bottom: 1.5rem;
        position: relative;
    }}

    .welcome-logo img {{
        height: 52px;
        width: auto;
    }}

    .welcome-card h2 {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
        position: relative;
        color: {COLORS['text_secondary']};
    }}

    .welcome-card p {{
        color: {COLORS['text_muted']};
        font-size: 0.88rem;
        position: relative;
        max-width: 480px;
        margin: 0 auto;
        line-height: 1.65;
    }}

    /* --- Empty state --- */
    .empty-state {{
        text-align: center;
        padding: 3rem 2rem;
    }}

    .empty-state-icon {{
        width: 64px; height: 64px;
        margin: 0 auto 1.25rem auto;
        border-radius: 20px;
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        animation: empty-float 4s ease-in-out infinite;
    }}

    @keyframes empty-float {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-6px); }}
    }}

    .empty-state h3 {{
        font-family: 'Space Grotesk', sans-serif;
        color: {COLORS['text_secondary']};
        font-weight: 500;
        font-size: 1rem;
        margin-bottom: 0.4rem;
    }}

    .empty-state p {{
        color: {COLORS['text_muted']};
        font-size: 0.85rem;
    }}

    .empty-state code {{
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        padding: 2px 8px;
        border-radius: 6px;
        font-family: 'Fira Code', monospace;
        font-size: 0.78rem;
    }}

    /* --- Duration badge --- */
    .duration-badge {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 8px;
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        font-family: 'Fira Code', monospace;
        font-size: 0.68rem;
        color: {COLORS['text_muted']};
        margin-top: 0.5rem;
    }}

    /* --- Metric widget --- */
    [data-testid="stMetric"] {{
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        border-radius: 16px;
        padding: 1rem;
        transition: border-color 0.25s ease;
    }}

    [data-testid="stMetric"]:hover {{
        border-color: {COLORS['border_hover']};
    }}

    /* --- Buttons --- */
    .stButton > button {{
        border-radius: 10px;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        border: 1px solid {COLORS['glass_border']};
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }}

    .stButton > button:active {{
        transform: scale(0.97);
    }}

    /* --- Dataframe --- */
    .stDataFrame {{
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid {COLORS['glass_border']};
    }}

    /* --- Chart container --- */
    .chart-container {{
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        border-radius: 16px;
        padding: 1.25rem;
        margin: 0.5rem 0;
    }}

    .chart-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.75rem;
        font-weight: 500;
        color: {COLORS['text_secondary']};
        margin-bottom: 0.5rem;
        letter-spacing: 0.02em;
    }}

    /* --- Plotly --- */
    .js-plotly-plot .plotly .modebar {{ background: transparent !important; }}

    /* --- Scrollbar --- */
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {COLORS['glass_border']}; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLORS['text_muted']}; }}

    /* --- Page title --- */
    .page-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.35rem;
        font-weight: 600;
        background: {COLORS['brand_gradient']};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.15rem;
    }}

    .page-subtitle {{
        font-family: 'Fira Code', monospace;
        font-size: 0.75rem;
        color: {COLORS['text_muted']};
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Ambient glow blobs
st.markdown(
    '<div class="ambient-glow a"></div>'
    '<div class="ambient-glow b"></div>'
    '<div class="ambient-glow c"></div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers API
# ---------------------------------------------------------------------------
def api_health() -> tuple[bool, str]:
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return r.status_code == 200, r.text
    except requests.RequestException as e:
        return False, str(e)


def api_ask(question: str) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return True, r.json().get("reponse", "")
    except requests.RequestException as e:
        return False, f"Erreur API : {e}"


def api_metrics() -> dict | None:
    try:
        r = requests.get(f"{API_BASE_URL}/metrics", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def api_recent(limit: int = 50) -> list[dict]:
    try:
        r = requests.get(
            f"{API_BASE_URL}/metrics/recent",
            params={"limit": limit},
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("records", [])
    except requests.RequestException:
        return []


def save_upload(uploaded_file) -> Path:
    """Sauvegarde un fichier uploade dans data/uploads/ avec un nom unique."""
    fname = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
    dest = UPLOAD_DIR / fname
    dest.write_bytes(uploaded_file.getbuffer())
    return dest


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
def render_kpi(label: str, value: str, sublabel: str = "", accent_color: str = ""):
    """Affiche une carte KPI glassmorphism."""
    sub_html = f'<div class="kpi-sublabel">{sublabel}</div>' if sublabel else ""
    color_style = f' style="color: {accent_color};"' if accent_color else ""
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value"{color_style}>{value}</div>'
        f"{sub_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_health_gauge(label: str, value: float, thresholds: tuple[float, float] = (0.0, 0.05)):
    """Affiche une gauge de sante avec barre de progression."""
    pct = min(value * 100, 100)
    bar_width = 0 if pct == 0 else max(3, pct)

    if value <= thresholds[0]:
        cls, text_cls = "gauge-good", "text-good"
    elif value <= thresholds[1]:
        cls, text_cls = "gauge-warn", "text-warn"
    else:
        cls, text_cls = "gauge-bad", "text-bad"

    st.markdown(
        f'<div class="health-gauge">'
        f'  <div class="gauge-header">'
        f'    <span class="gauge-label">{label}</span>'
        f'    <span class="gauge-value {text_cls}">{pct:.1f}%</span>'
        f"  </div>"
        f'  <div class="gauge-bar">'
        f'    <div class="gauge-fill {cls}" style="width: {bar_width}%;"></div>'
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def plotly_dark_layout(fig):
    """Applique le theme Pulse dark au graphique Plotly."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", size=11, color=COLORS["text_muted"]),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.03)",
            zerolinecolor="rgba(255,255,255,0.03)",
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.03)",
            zerolinecolor="rgba(255,255,255,0.03)",
            showgrid=True,
        ),
        hoverlabel=dict(
            bgcolor=COLORS["bg_card_solid"],
            bordercolor=COLORS["brand_blue"],
            font_size=11,
            font_family="Fira Code, monospace",
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    # Logo
    if LOGO_B64:
        st.markdown(
            f'<div class="sidebar-logo">'
            f'<img src="data:image/svg+xml;base64,{LOGO_B64}" alt="Pulse logo"/>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("# Pulse")

    # Status
    ok, msg = api_health()
    if ok:
        st.markdown(
            '<div class="status-badge status-online">'
            '<div class="pulse-dot"></div>'
            " En ligne"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-badge status-offline">'
            "&#x25CF;&nbsp; Hors ligne"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(msg)

    # Navigation
    st.markdown(
        '<div class="section-header"><span class="section-dot"></span> Navigation</div>',
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        ["Chat", "Dashboard"],
        label_visibility="collapsed",
        format_func=lambda x: f"{'💬' if x == 'Chat' else '📊'}  {x}",
    )

    # Info
    st.markdown(
        '<div class="section-header"><span class="section-dot"></span> Systeme</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Architecture"):
        st.markdown(
            "**Backend** : FastAPI (`api.py`)\n\n"
            "**Agent** : ReAct (Reason / Act / Observe)\n\n"
            "**Outils** : SQL, RAG, web, audio, image\n\n"
            "**Monitoring** : M5E5"
        )

    st.markdown(
        f'<div style="position:fixed; bottom:1rem; font-size:0.62rem; '
        f'color:{COLORS["text_muted"]}; font-family:Fira Code,monospace; '
        f'opacity:0.5;">'
        f"Pulse v{BRAND['version']} &middot; Formation IA"
        f"</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# Page 1 — Chat
# ===========================================================================
EXAMPLE_QUESTIONS = [
    ("Briefing actu", "Fais-moi un briefing des dernieres actualites tech"),
    ("Stats base", "Combien d'articles sont stockes en base ?"),
    ("Recherche IA", "Recherche des articles sur l'intelligence artificielle"),
]


def page_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- Welcome ---
    if not st.session_state.messages:
        logo_html = ""
        if LOGO_B64:
            logo_html = (
                f'<div class="welcome-logo">'
                f'<img src="data:image/svg+xml;base64,{LOGO_B64}" alt="Pulse"/>'
                f"</div>"
            )

        st.markdown(
            f'<div class="welcome-card">'
            f"{logo_html}"
            f"<h2>Votre agent de veille technologique</h2>"
            f"<p>Interrogez la base d'articles RSS, demandez un briefing actualites, "
            f"ou deposez un fichier audio/image a analyser.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        cols = st.columns(len(EXAMPLE_QUESTIONS))
        for i, (short, full) in enumerate(EXAMPLE_QUESTIONS):
            with cols[i]:
                if st.button(short, key=f"example_{i}", use_container_width=True):
                    st.session_state._pending_question = full
                    st.rerun()
    else:
        msg_count = len(st.session_state.messages)
        st.markdown(
            f'<div style="margin-bottom:1.5rem;">'
            f'<div class="page-title">Conversation</div>'
            f'<div class="page-subtitle">'
            f"{msg_count} message{'s' if msg_count > 1 else ''}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # --- Upload ---
    with st.expander("Joindre un fichier (audio ou image)"):
        col_a, col_b = st.columns(2)
        with col_a:
            audio_file = st.file_uploader(
                "Audio",
                type=["mp3", "wav", "m4a", "ogg", "webm"],
                key="audio_upload",
            )
        with col_b:
            image_file = st.file_uploader(
                "Image",
                type=["jpg", "jpeg", "png", "webp"],
                key="image_upload",
            )
        if audio_file:
            st.audio(audio_file)
        if image_file:
            st.image(image_file, width=250)

    # --- History ---
    for msg in st.session_state.messages:
        avatar = (
            "https://api.iconify.design/lucide/bot.svg"
            if msg["role"] == "assistant"
            else "https://api.iconify.design/lucide/user.svg"
        )
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("duration_s") is not None:
                st.markdown(
                    f'<div class="duration-badge">&#x23F1; {msg["duration_s"]:.2f}s</div>',
                    unsafe_allow_html=True,
                )

    # --- Pending ---
    pending = st.session_state.pop("_pending_question", None)

    # --- Input ---
    prompt = st.chat_input("Posez votre question a Pulse...")

    if prompt is None and pending is not None:
        prompt = pending

    if prompt:
        final_prompt = prompt
        attachment_note = ""

        if audio_file is not None:
            path = save_upload(audio_file)
            rel_path = path.relative_to(UPLOAD_DIR.parent.parent)
            final_prompt = f"{prompt}\n\nFichier audio a analyser : {rel_path}"
            attachment_note = f"\n\n*audio joint : `{rel_path}`*"
        elif image_file is not None:
            path = save_upload(image_file)
            rel_path = path.relative_to(UPLOAD_DIR.parent.parent)
            final_prompt = f"{prompt}\n\nFichier image a analyser : {rel_path}"
            attachment_note = f"\n\n*image jointe : `{rel_path}`*"

        st.session_state.messages.append(
            {"role": "user", "content": prompt + attachment_note}
        )
        with st.chat_message("user", avatar="https://api.iconify.design/lucide/user.svg"):
            st.markdown(prompt + attachment_note)

        with st.chat_message("assistant", avatar="https://api.iconify.design/lucide/bot.svg"):
            typing_placeholder = st.empty()
            typing_placeholder.markdown(
                '<div class="typing-indicator">'
                '<span class="dot"></span><span class="dot"></span><span class="dot"></span>'
                '<span class="typing-label">Pulse reflechit...</span>'
                "</div>",
                unsafe_allow_html=True,
            )

            t0 = time.monotonic()
            ok_resp, reply = api_ask(final_prompt)
            duration = time.monotonic() - t0

            typing_placeholder.empty()

            if not ok_resp:
                st.error(reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Erreur : {reply}", "duration_s": duration}
                )
            else:
                st.markdown(reply)
                st.markdown(
                    f'<div class="duration-badge">&#x23F1; {duration:.2f}s</div>',
                    unsafe_allow_html=True,
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply, "duration_s": duration}
                )

    # --- Controls ---
    if st.session_state.messages:
        col1, col2, _ = st.columns([1, 1, 6])
        with col1:
            if st.button("Effacer", type="secondary"):
                st.session_state.messages = []
                st.rerun()
        with col2:
            st.download_button(
                "Exporter",
                data="\n\n".join(
                    f"**{m['role']}** : {m['content']}"
                    for m in st.session_state.messages
                ),
                file_name=f"pulse_conversation_{datetime.now():%Y%m%d_%H%M%S}.md",
                mime="text/markdown",
            )


# ===========================================================================
# Page 2 — Dashboard
# ===========================================================================
def page_dashboard():
    st.markdown(
        '<div style="margin-bottom:1.5rem;">'
        '<div class="page-title">Dashboard Monitoring</div>'
        '<div class="page-subtitle">/metrics &middot; /metrics/recent</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    col_refresh, col_auto, _ = st.columns([1, 2, 5])
    with col_refresh:
        if st.button("Rafraichir", type="secondary"):
            st.rerun()
    with col_auto:
        auto = st.checkbox("Auto-refresh (10s)", value=False)

    metrics = api_metrics()
    if metrics is None:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-state-icon">&#x1F6F0;</div>'
            "<h3>API non disponible</h3>"
            "<p>Lancez l'API avec <code>uvicorn api:app --reload</code></p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    if metrics["total_requests"] == 0:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-state-icon">&#x1F4AC;</div>'
            "<h3>En attente de donnees</h3>"
            "<p>Posez une question a Pulse dans l'onglet Chat.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # --- KPIs ---
    st.markdown(
        '<div class="section-header"><span class="section-dot"></span> Performance</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Requetes", str(metrics["total_requests"]), accent_color=COLORS["brand_blue"])
    with c2:
        render_kpi("Latence moy.", f"{metrics['avg_duration_ms']:.0f} ms")
    with c3:
        render_kpi("p95 Latence", f"{metrics['p95_duration_ms']:.0f} ms")
    with c4:
        render_kpi("Modele", metrics["model"], sublabel="OpenAI")

    st.markdown("", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        render_kpi("Tokens total", f"{metrics['total_tokens']:,}".replace(",", " "))
    with c6:
        render_kpi("Tokens / req", f"{metrics['avg_tokens_per_request']:.0f}")
    with c7:
        render_kpi("Cout total", f"${metrics['total_cost_usd']:.4f}", accent_color=COLORS["warning"])
    with c8:
        render_kpi("Cout / req", f"${metrics['avg_cost_per_request_usd']:.5f}")

    # --- Health ---
    st.markdown(
        '<div class="section-header"><span class="section-dot"></span> Sante</div>',
        unsafe_allow_html=True,
    )

    c9, c10, _ = st.columns([1, 1, 2])
    with c9:
        render_health_gauge("Taux d'erreur", metrics["error_rate"])
    with c10:
        render_health_gauge("Taux de fallback", metrics["fallback_rate"], thresholds=(0.0, 0.10))

    # --- Recent ---
    st.markdown(
        '<div class="section-header"><span class="section-dot"></span> Requetes recentes</div>',
        unsafe_allow_html=True,
    )

    records = api_recent(limit=50)
    if records:
        df = pd.DataFrame(records)

        if "duration_ms" in df.columns and len(df) > 1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title">Latence par requete (ms)</div>', unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=df["duration_ms"],
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLORS["brand_blue"], width=2, shape="spline"),
                fillcolor=COLORS["brand_glow"],
                hovertemplate="<b>%{y:.0f} ms</b><extra></extra>",
            ))
            plotly_dark_layout(fig)
            fig.update_layout(height=220, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "displayModeBar": False})

            st.markdown("</div>", unsafe_allow_html=True)

        if "total_tokens" in df.columns and len(df) > 1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title">Tokens consommes par requete</div>', unsafe_allow_html=True)

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                y=df["total_tokens"],
                marker=dict(
                    color=df["total_tokens"],
                    colorscale=[[0, "rgba(59,130,246,0.25)"], [0.5, COLORS["brand_blue"]], [1, COLORS["brand_indigo"]]],
                    line_width=0,
                ),
                opacity=0.85,
                hovertemplate="<b>%{y:,} tokens</b><extra></extra>",
            ))
            plotly_dark_layout(fig2)
            fig2.update_layout(height=180, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False, "displayModeBar": False})

            st.markdown("</div>", unsafe_allow_html=True)

        display_cols = [
            c for c in [
                "timestamp", "question", "duration_ms", "total_tokens",
                "cost_usd", "fallback", "fallback_reason", "error",
            ] if c in df.columns
        ]
        st.dataframe(df[display_cols].iloc[::-1], use_container_width=True, hide_index=True)

    if auto:
        time.sleep(10)
        st.rerun()


# ===========================================================================
# Router
# ===========================================================================
if page == "Chat":
    page_chat()
else:
    page_dashboard()
