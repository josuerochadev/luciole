"""
API FastAPI pour l'agent de veille technologique.
- M5E4 : containerisation Docker (POST /ask, GET /health).
- M5E5 : monitoring + KPIs (GET /metrics, GET /metrics/recent).
- Pulse_ : interface éditoriale HTML (GET /, GET /about).
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from main import agent_react
from monitoring import (
    end_request,
    get_metrics,
    get_recent,
    start_request,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="pulse_ · Tech Intelligence Agent", version="2.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    reponse: str


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request, "index.html", {"active_page": "chat"})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {"active_page": "about"})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"active_page": "dashboard"})


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
