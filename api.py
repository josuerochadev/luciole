"""
API FastAPI pour l'agent de veille technologique.
- M5E4 : containerisation Docker (POST /ask, GET /health).
- M5E5 : monitoring + KPIs (GET /metrics, GET /metrics/recent).
"""
from fastapi import FastAPI
from pydantic import BaseModel

from main import agent_react
from monitoring import (
    end_request,
    get_metrics,
    get_recent,
    start_request,
)

app = FastAPI(title="Agent Veille Technologique", version="1.1.0")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    reponse: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    start_request(req.question)
    try:
        reponse = agent_react(req.question)
    except Exception as exc:  # noqa: BLE001 — on veut tout capturer pour le monitoring
        end_request(error=f"{type(exc).__name__}: {exc}")
        raise
    end_request()
    return AskResponse(reponse=reponse)


@app.get("/metrics")
def metrics():
    """Agrégats de monitoring (M5E5)."""
    return get_metrics()


@app.get("/metrics/recent")
def metrics_recent(limit: int = 20):
    """Les N dernières requêtes enregistrées (debug)."""
    records = get_recent(limit=limit)
    return {"count": len(records), "records": records}
