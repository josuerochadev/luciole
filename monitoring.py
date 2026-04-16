"""
Monitoring de l'agent fil-rouge (M5E5).

Enregistre chaque requête utilisateur (question, durée, tokens, coût estimé, erreur,
fallback) et expose des agrégats pour l'endpoint GET /metrics.

Conçu pour être optionnel : les fonctions sont des no-op si aucun contexte de
requête n'est actif (par exemple en mode CLI via `python main.py`).
"""
from __future__ import annotations

import contextvars
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tarifs OpenAI — gpt-4o-mini (USD / 1M tokens, barème 2025-11)
# Input  : 0.150 $ / 1M tokens
# Output : 0.600 $ / 1M tokens
# Cf. https://openai.com/api/pricing/
# ---------------------------------------------------------------------------
PRICE_INPUT_PER_1M_USD = 0.15
PRICE_OUTPUT_PER_1M_USD = 0.60
MODEL_LABEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Stockage
# ---------------------------------------------------------------------------
_records: list[dict[str, Any]] = []
_lock = threading.Lock()

# Chemin optionnel pour persister les requêtes en JSONL (désactivé par défaut)
METRICS_LOG_FILE: Path | None = None

# Contexte par requête (compatible async/threads via contextvars)
_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "monitoring_ctx", default=None
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Estime le coût d'un appel LLM en USD (barème gpt-4o-mini)."""
    return (
        prompt_tokens * PRICE_INPUT_PER_1M_USD
        + completion_tokens * PRICE_OUTPUT_PER_1M_USD
    ) / 1_000_000


def _percentile(values: list[float], p: float) -> float:
    """Percentile simple (interpolation linéaire, p dans [0, 1])."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


# ---------------------------------------------------------------------------
# API publique — cycle de vie d'une requête
# ---------------------------------------------------------------------------
def start_request(question: str) -> dict:
    """Ouvre un contexte de monitoring pour la requête courante."""
    ctx = {
        "question": question,
        "start": time.monotonic(),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "llm_calls": 0,
        "fallback": False,
        "fallback_reason": None,
    }
    _ctx.set(ctx)
    return ctx


def add_llm_usage(prompt_tokens: int, completion_tokens: int) -> None:
    """Accumule la consommation d'un appel LLM dans le contexte courant.

    No-op si aucun contexte actif (ex. CLI ou test unitaire).
    """
    ctx = _ctx.get()
    if ctx is None:
        return
    ctx["prompt_tokens"] += int(prompt_tokens or 0)
    ctx["completion_tokens"] += int(completion_tokens or 0)
    ctx["llm_calls"] += 1


def mark_fallback(reason: str = "") -> None:
    """Marque la requête courante comme ayant subi un fallback.

    Un fallback correspond à : blocage sécurité, boucle répétée (même outil
    essayé deux fois), ou dépassement de MAX_ITERATIONS.
    """
    ctx = _ctx.get()
    if ctx is None:
        return
    ctx["fallback"] = True
    ctx["fallback_reason"] = reason or ctx["fallback_reason"]


def end_request(error: str | None = None) -> dict:
    """Clôture la requête courante et l'ajoute aux records."""
    ctx = _ctx.get()
    if ctx is None:
        return {}

    duration_ms = (time.monotonic() - ctx["start"]) * 1000
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": (ctx["question"] or "")[:200],
        "duration_ms": round(duration_ms, 1),
        "prompt_tokens": ctx["prompt_tokens"],
        "completion_tokens": ctx["completion_tokens"],
        "total_tokens": ctx["prompt_tokens"] + ctx["completion_tokens"],
        "llm_calls": ctx["llm_calls"],
        "cost_usd": round(
            _estimate_cost_usd(ctx["prompt_tokens"], ctx["completion_tokens"]), 6
        ),
        "error": error,
        "fallback": ctx["fallback"],
        "fallback_reason": ctx["fallback_reason"],
    }

    with _lock:
        _records.append(record)
        if METRICS_LOG_FILE is not None:
            try:
                METRICS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
                with METRICS_LOG_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except OSError as e:
                logger.warning(f"[monitoring] Impossible d'écrire le log : {e}")

    _ctx.set(None)
    return record


# ---------------------------------------------------------------------------
# API publique — lecture des métriques
# ---------------------------------------------------------------------------
def get_metrics() -> dict:
    """Retourne les agrégats de toutes les requêtes enregistrées."""
    with _lock:
        records = list(_records)

    n = len(records)
    if n == 0:
        return {
            "model": MODEL_LABEL,
            "total_requests": 0,
            "avg_duration_ms": 0.0,
            "p95_duration_ms": 0.0,
            "total_tokens": 0,
            "avg_tokens_per_request": 0.0,
            "total_cost_usd": 0.0,
            "avg_cost_per_request_usd": 0.0,
            "error_rate": 0.0,
            "fallback_rate": 0.0,
        }

    durations = [r["duration_ms"] for r in records]
    total_tokens = sum(r["total_tokens"] for r in records)
    total_cost = sum(r["cost_usd"] for r in records)
    errors = sum(1 for r in records if r["error"])
    fallbacks = sum(1 for r in records if r["fallback"])

    return {
        "model": MODEL_LABEL,
        "total_requests": n,
        "avg_duration_ms": round(sum(durations) / n, 1),
        "p95_duration_ms": round(_percentile(durations, 0.95), 1),
        "total_tokens": total_tokens,
        "avg_tokens_per_request": round(total_tokens / n, 1),
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_per_request_usd": round(total_cost / n, 6),
        "error_rate": round(errors / n, 4),
        "fallback_rate": round(fallbacks / n, 4),
    }


def get_recent(limit: int = 20) -> list[dict]:
    """Retourne les `limit` dernières requêtes enregistrées (ordre chronologique)."""
    with _lock:
        return list(_records[-limit:])


def reset() -> None:
    """Réinitialise les records (utile pour les tests)."""
    with _lock:
        _records.clear()
