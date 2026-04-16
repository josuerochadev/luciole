"""
Interface utilisateur Streamlit pour l'agent de veille technologique.

Consomme l'API FastAPI du fil-rouge (api.py) :
- POST /ask           : envoi d'une requête
- GET  /health        : healthcheck
- GET  /metrics       : agrégats de monitoring (M5E5)
- GET  /metrics/recent: dernières requêtes

Lancement :
    # 1) Démarrer l'API (dans un terminal)
    cd fil-rouge && uvicorn api:app --reload

    # 2) Démarrer l'UI (dans un autre terminal)
    cd fil-rouge && streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000")
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 120  # l'agent peut être lent (appels LLM multiples)

st.set_page_config(
    page_title="Agent Veille Tech",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
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
    """Sauvegarde un fichier uploadé dans data/uploads/ avec un nom unique."""
    suffix = Path(uploaded_file.name).suffix
    fname = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
    dest = UPLOAD_DIR / fname
    dest.write_bytes(uploaded_file.getbuffer())
    return dest


# ---------------------------------------------------------------------------
# Sidebar — statut + navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🛰️ Agent Veille")
    st.caption("UI Streamlit — fil rouge")

    ok, msg = api_health()
    if ok:
        st.success(f"API OK · {API_BASE_URL}")
    else:
        st.error(f"API KO · {API_BASE_URL}")
        st.caption(msg)

    page = st.radio(
        "Navigation",
        ["💬 Chat", "📊 Dashboard"],
        label_visibility="collapsed",
    )

    st.divider()
    with st.expander("ℹ️ À propos"):
        st.markdown(
            "- **Backend** : FastAPI (`api.py`)\n"
            "- **Agent** : ReAct (Reason → Act → Observe)\n"
            "- **Outils** : SQL, RAG, web, audio, image\n"
            "- **Monitoring** : M5E5"
        )


# ===========================================================================
# Page 1 — Chat
# ===========================================================================
def page_chat():
    st.title("💬 Conversation avec l'agent")
    st.caption(
        "Pose une question (briefing actus, requête SQL interne, recherche "
        "d'archives RSS) ou dépose un fichier audio/image à analyser."
    )

    # --- Initialiser l'historique ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- Zone d'upload (optionnel) ---
    with st.expander("📎 Joindre un fichier (audio ou image)"):
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

    # --- Afficher l'historique ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("duration_s") is not None:
                st.caption(f"⏱️ {msg['duration_s']:.2f}s")

    # --- Input utilisateur ---
    if prompt := st.chat_input("Votre question…"):
        # Si un fichier est joint, on enrichit la question avec son chemin
        final_prompt = prompt
        attachment_note = ""

        if audio_file is not None:
            path = save_upload(audio_file)
            rel_path = path.relative_to(UPLOAD_DIR.parent.parent)
            final_prompt = f"{prompt}\n\nFichier audio à analyser : {rel_path}"
            attachment_note = f"\n\n*📎 audio joint : `{rel_path}`*"

        elif image_file is not None:
            path = save_upload(image_file)
            rel_path = path.relative_to(UPLOAD_DIR.parent.parent)
            final_prompt = f"{prompt}\n\nFichier image à analyser : {rel_path}"
            attachment_note = f"\n\n*📎 image jointe : `{rel_path}`*"

        # Afficher la question utilisateur
        st.session_state.messages.append(
            {"role": "user", "content": prompt + attachment_note}
        )
        with st.chat_message("user"):
            st.markdown(prompt + attachment_note)

        # Appel API
        with st.chat_message("assistant"):
            with st.spinner("L'agent réfléchit…"):
                t0 = time.monotonic()
                ok, reply = api_ask(final_prompt)
                duration = time.monotonic() - t0

            if not ok:
                st.error(reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"❌ {reply}", "duration_s": duration}
                )
            else:
                st.markdown(reply)
                st.caption(f"⏱️ {duration:.2f}s")
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply, "duration_s": duration}
                )

    # --- Boutons de contrôle ---
    if st.session_state.messages:
        col1, col2, _ = st.columns([1, 1, 6])
        with col1:
            if st.button("🗑️ Effacer"):
                st.session_state.messages = []
                st.rerun()
        with col2:
            st.download_button(
                "💾 Exporter",
                data="\n\n".join(
                    f"**{m['role']}** : {m['content']}"
                    for m in st.session_state.messages
                ),
                file_name=f"conversation_{datetime.now():%Y%m%d_%H%M%S}.md",
                mime="text/markdown",
            )


# ===========================================================================
# Page 2 — Dashboard
# ===========================================================================
def page_dashboard():
    st.title("📊 Dashboard monitoring")
    st.caption("Données issues de `/metrics` et `/metrics/recent` (M5E5).")

    col_refresh, col_auto = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Rafraîchir"):
            st.rerun()
    with col_auto:
        auto = st.checkbox("Auto-refresh (10s)", value=False)

    metrics = api_metrics()
    if metrics is None:
        st.error("Impossible de récupérer les métriques. L'API est-elle démarrée ?")
        return

    if metrics["total_requests"] == 0:
        st.info("Aucune requête enregistrée pour l'instant. Va poser une question dans l'onglet Chat.")
        return

    # --- KPIs principaux ---
    st.subheader("Indicateurs clés")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Requêtes", metrics["total_requests"])
    c2.metric("Latence moy.", f"{metrics['avg_duration_ms']:.0f} ms")
    c3.metric("p95 latence", f"{metrics['p95_duration_ms']:.0f} ms")
    c4.metric("Modèle", metrics["model"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Tokens total", f"{metrics['total_tokens']:,}".replace(",", " "))
    c6.metric("Tokens / req", f"{metrics['avg_tokens_per_request']:.0f}")
    c7.metric("Coût total", f"${metrics['total_cost_usd']:.4f}")
    c8.metric("Coût / req", f"${metrics['avg_cost_per_request_usd']:.5f}")

    # --- Taux d'erreur / fallback ---
    st.subheader("Santé")
    c9, c10 = st.columns(2)
    err = metrics["error_rate"]
    fb = metrics["fallback_rate"]
    c9.metric(
        "Taux d'erreur",
        f"{err*100:.1f}%",
        delta="🟢 OK" if err == 0 else "🔴",
        delta_color="off",
    )
    c10.metric(
        "Taux de fallback",
        f"{fb*100:.1f}%",
        delta="🟢 OK" if fb == 0 else "🟡",
        delta_color="off",
    )

    # --- Requêtes récentes ---
    st.subheader("Requêtes récentes")
    records = api_recent(limit=50)
    if records:
        df = pd.DataFrame(records)

        # Graphique latence
        if "duration_ms" in df.columns and len(df) > 1:
            st.line_chart(df["duration_ms"], height=200, use_container_width=True)

        # Tableau détaillé
        display_cols = [
            c
            for c in [
                "timestamp",
                "question",
                "duration_ms",
                "total_tokens",
                "cost_usd",
                "fallback",
                "fallback_reason",
                "error",
            ]
            if c in df.columns
        ]
        st.dataframe(
            df[display_cols].iloc[::-1],  # ordre chronologique inverse (plus récent en haut)
            use_container_width=True,
            hide_index=True,
        )

    # Auto-refresh simple
    if auto:
        time.sleep(10)
        st.rerun()


# ===========================================================================
# Router
# ===========================================================================
if page.startswith("💬"):
    page_chat()
else:
    page_dashboard()
