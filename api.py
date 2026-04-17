"""
API FastAPI pour l'agent de veille technologique.
- M5E4 : containerisation Docker (POST /ask, GET /health).
- M5E5 : monitoring + KPIs (GET /metrics, GET /metrics/recent).
- M6   : digest endpoints (GET /digest, POST /digest/send).
- Luciole_ : interface éditoriale HTML (GET /, GET /about).
"""
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
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
from tools.database import noter_article
from tools.email import envoyer_rapport, generer_html, selectionner_articles

API_KEY = os.getenv("API_KEY", "luciole-secret-key")

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="luciole_ · Tech Intelligence Agent", version="2.0.0")
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


# ---------------------------------------------------------------------------
# Digest endpoints (M6)
# ---------------------------------------------------------------------------

def _verifier_api_key(x_api_key: str | None):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide ou manquante.")


@app.get("/digest", response_class=HTMLResponse)
def digest(limit: int = 20):
    """Retourne le HTML du digest sans envoyer d'email."""
    articles = selectionner_articles(nb_max=limit)
    return HTMLResponse(content=generer_html(articles))


# ---------------------------------------------------------------------------
# Feedback utilisateur (amélioration continue RAG)
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    article_url: str
    score: int


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """Enregistre un feedback utilisateur sur un article (score 1-10)."""
    try:
        result = noter_article(req.article_url, req.score)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


class DigestSendRequest(BaseModel):
    destinataires: list[str] | None = None
    dry_run: bool = False


@app.post("/digest/send")
def digest_send(
    req: DigestSendRequest | None = None,
    x_api_key: str | None = Header(default=None),
):
    """Déclenche l'envoi du digest par email. Protégé par X-API-Key."""
    _verifier_api_key(x_api_key)
    body = req or DigestSendRequest()
    return envoyer_rapport(
        destinataires=body.destinataires,
        dry_run=body.dry_run,
    )
