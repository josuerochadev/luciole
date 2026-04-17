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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from main import agent_react
from monitoring import (
    end_request,
    get_metrics,
    get_recent,
    start_request,
)
from tools.database import charger_json, noter_article
from tools.email import envoyer_rapport, generer_html, selectionner_articles
from config import HISTORIQUE_FILE

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("Variable d'environnement API_KEY obligatoire. Définissez-la avant de lancer l'API.")

BASE_DIR = Path(__file__).resolve().parent

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="luciole_ · Tech Intelligence Agent", version="2.0.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# CORS — restreindre aux origines autorisées
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


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
@limiter.limit("10/minute")
def ask(request: Request, req: AskRequest, x_api_key: str | None = Header(default=None)):
    _verifier_api_key(x_api_key, request)
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

def _is_same_origin(request: Request) -> bool:
    """Vérifie si la requête provient du frontend servi par ce même serveur.
    Supporte les reverse proxies (Render, etc.) via X-Forwarded-Host."""
    referer = request.headers.get("referer", "")
    origin = request.headers.get("origin", "")
    # Derrière un reverse proxy, host peut être l'IP interne
    host = request.headers.get("x-forwarded-host", "") or request.headers.get("host", "")
    return host and (referer.startswith(f"http://{host}") or referer.startswith(f"https://{host}")
                     or origin == f"http://{host}" or origin == f"https://{host}")


def _verifier_api_key(x_api_key: str | None, request: Request | None = None):
    if request and _is_same_origin(request):
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide ou manquante.")


@app.get("/digest-page", response_class=HTMLResponse)
async def digest_page(request: Request):
    """Page de gestion du digest email."""
    return templates.TemplateResponse(request, "digest.html", {"active_page": "digest"})


@app.get("/digest", response_class=HTMLResponse)
def digest(limit: int = 20):
    """Retourne le HTML du digest sans envoyer d'email."""
    articles = selectionner_articles(nb_max=limit)
    return HTMLResponse(content=generer_html(articles))


@app.get("/digest/stats")
def digest_stats():
    """Stats rapides pour la page digest."""
    articles = selectionner_articles(nb_max=100)
    categories = set(a.get("categorie", "Autre") for a in articles)
    historique = charger_json(HISTORIQUE_FILE)
    return {
        "nb_articles": len(articles),
        "nb_categories": len(categories),
        "nb_envois": len(historique),
    }


@app.get("/digest/history")
def digest_history():
    """Historique des envois de digest."""
    historique = charger_json(HISTORIQUE_FILE)
    return {"historique": historique}


# ---------------------------------------------------------------------------
# Feedback utilisateur (amélioration continue RAG)
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    article_url: str
    score: int


@app.post("/feedback")
@limiter.limit("30/minute")
def feedback(request: Request, req: FeedbackRequest, x_api_key: str | None = Header(default=None)):
    """Enregistre un feedback utilisateur sur un article (score 1-10)."""
    _verifier_api_key(x_api_key)
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
