"""
API FastAPI pour l'agent de veille technologique.
- M5E4 : containerisation Docker (POST /ask, GET /health).
- M5E5 : monitoring + KPIs (GET /metrics, GET /metrics/recent).
- M6   : digest endpoints (GET /digest, POST /digest/send).
- Luciole_ : interface éditoriale HTML (GET /, GET /about).
- Phase 1 : historique des conversations persistant (SQLite).
- Phase 2 : comptes utilisateurs et authentification (JWT).
"""
import logging
import os
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from main import agent_react, agent_react_stream
from monitoring import (
    end_request,
    get_metrics,
    get_recent,
    start_request,
)
from tools.database import charger_json, noter_article
from tools.email import envoyer_rapport, generer_html, selectionner_articles
from config import HISTORIQUE_FILE, UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_TYPES, UPLOAD_TTL
from database import (
    create_conversation,
    create_user,
    get_user_by_email,
    list_conversations,
    get_conversation,
    get_conversation_messages,
    add_message,
    delete_conversation,
    update_conversation_title,
    get_recent_messages,
    save_response_feedback,
    get_response_feedback_stats,
)
from llm import appeler_llm
from auth import (
    COOKIE_NAME,
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

# Cookie secure=True uniquement en prod (HTTPS). En dev localhost, secure=False.
IS_PROD = bool(os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("FLY_APP_NAME"))
COOKIE_SECURE = IS_PROD

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
        allow_methods=["GET", "POST", "DELETE", "PATCH"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
# Cache-buster: changes on each server restart to force browser to reload static assets
import hashlib
_cache_bust = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
templates.env.globals["cache_bust"] = _cache_bust


# ---------------------------------------------------------------------------
# Upload helpers (Phase 4)
# ---------------------------------------------------------------------------

def _validate_magic_bytes(data: bytes, declared_type: str) -> bool:
    """Valide le type de fichier via magic bytes, pas seulement l'extension."""
    if declared_type in ("image/png",):
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if declared_type in ("image/jpeg",):
        return data[:3] == b"\xff\xd8\xff"
    if declared_type in ("image/webp",):
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if declared_type in ("application/pdf",):
        return data[:4] == b"%PDF"
    if declared_type in ("audio/mpeg",):
        return data[:3] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2") or data[:3] == b"ID3"
    if declared_type in ("audio/wav",):
        return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if declared_type in ("audio/mp4",):
        # MP4/M4A: ftyp box after size bytes
        return b"ftyp" in data[:12]
    return False


def _cleanup_expired_uploads():
    """Supprime les fichiers uploadés expirés (TTL dépassé)."""
    now = time.time()
    upload_path = Path(UPLOAD_DIR)
    if not upload_path.exists():
        return
    count = 0
    for f in upload_path.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > UPLOAD_TTL:
            f.unlink(missing_ok=True)
            count += 1
    if count:
        logger.info(f"[Upload] Nettoyage : {count} fichier(s) expiré(s) supprimé(s)")


# Nettoyage périodique via tâche de fond
from contextlib import asynccontextmanager
import asyncio

_cleanup_task = None

async def _periodic_cleanup():
    """Tâche de fond pour nettoyer les uploads expirés."""
    while True:
        await asyncio.sleep(600)  # Toutes les 10 minutes
        try:
            _cleanup_expired_uploads()
        except Exception as e:
            logger.error(f"[Upload] Erreur nettoyage : {e}")


@app.on_event("startup")
async def start_cleanup_task():
    global _cleanup_task
    _cleanup_task = asyncio.create_task(_periodic_cleanup())


@app.on_event("shutdown")
async def stop_cleanup_task():
    if _cleanup_task:
        _cleanup_task.cancel()


# ---------------------------------------------------------------------------
# Upload endpoint (Phase 4)
# ---------------------------------------------------------------------------

@app.post("/upload")
@limiter.limit("20/minute")
async def upload_file(request: Request, file: UploadFile = File(...), user=Depends(get_optional_user)):

    # Valider le type MIME déclaré
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé : {file.content_type}. "
                   f"Types acceptés : {', '.join(sorted(ALLOWED_TYPES))}",
        )

    # Lire le contenu et vérifier la taille
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(data) // (1024*1024)} MB). Maximum : {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    # Valider les magic bytes
    if not _validate_magic_bytes(data, file.content_type):
        raise HTTPException(
            status_code=400,
            detail="Le contenu du fichier ne correspond pas au type déclaré.",
        )

    # Sauvegarder avec un nom unique
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    file_id = uuid.uuid4().hex
    safe_name = f"{file_id}{ext}"
    file_path = Path(UPLOAD_DIR) / safe_name

    file_path.write_bytes(data)
    logger.info(f"[Upload] Fichier sauvegardé : {safe_name} ({len(data)} octets, {file.content_type})")

    return {
        "file_id": file_id,
        "filename": file.filename,
        "type": file.content_type,
        "size": len(data),
    }


# Servir les fichiers uploadés pour affichage dans le chat
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ---------------------------------------------------------------------------
# Auth endpoints (Phase 2)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_optional_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"active_page": "login", "user": None})


@app.post("/auth/register")
@limiter.limit("5/minute")
async def auth_register(request: Request, req: RegisterRequest):
    # Check if email already exists
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email.")

    pw_hash = hash_password(req.password)
    user = create_user(
        email=req.email,
        password_hash=pw_hash,
        display_name=req.display_name or req.email.split("@")[0],
    )

    token = create_access_token(user["id"])
    response = JSONResponse(content={"ok": True, "display_name": user["display_name"]})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=86400,
    )
    return response


@app.post("/auth/login")
@limiter.limit("10/minute")
async def auth_login(request: Request, req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    token = create_access_token(user["id"])
    response = JSONResponse(content={"ok": True, "display_name": user["display_name"]})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=86400,
    )
    return response


@app.post("/auth/logout")
async def auth_logout():
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(key=COOKIE_NAME)
    return response


@app.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Non authentifié.")
    return {"id": user["id"], "email": user["email"], "display_name": user["display_name"]}


# ---------------------------------------------------------------------------
# Pages HTML (protégées par auth)
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None
    file_id: str | None = None


class AskResponse(BaseModel):
    reponse: str
    conversation_id: str


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "index.html", {"active_page": "chat", "user": user})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, user=Depends(get_optional_user)):
    return templates.TemplateResponse(request, "about.html", {"active_page": "about", "user": user})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(request, "dashboard.html", {"active_page": "dashboard", "user": user})


@app.get("/health")
def health():
    return {"status": "ok"}


def _generate_title(question: str) -> str:
    """Génère un titre court pour une conversation à partir du 1er message."""
    try:
        title = appeler_llm(
            f"Génère un titre très court (5 mots max) pour cette conversation. "
            f"Réponds UNIQUEMENT avec le titre, sans guillemets ni ponctuation finale.\n\n"
            f"Message : {question}",
            system_prompt="Tu génères des titres courts et descriptifs.",
        )
        return title.strip().strip('"').strip("'")[:80]
    except Exception as e:
        logger.warning(f"Échec génération titre : {e}")
        return question[:50] + ("…" if len(question) > 50 else "")


@app.post("/ask")
@limiter.limit("10/minute")
async def ask(request: Request, req: AskRequest, user=Depends(get_optional_user)):
    # Créer ou récupérer la conversation (seulement si connecté)
    conv_id = req.conversation_id
    is_new = False
    if user:
        if not conv_id:
            conv = create_conversation(user_id=user["id"])
            conv_id = conv["id"]
            is_new = True
        else:
            conv = get_conversation(conv_id)
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation introuvable.")
    else:
        # Visiteur anonyme : pas de persistance
        conv_id = None

    # Résoudre le fichier uploadé si file_id est fourni
    enriched_question = req.question
    file_meta = None
    if req.file_id:
        # Chercher le fichier dans UPLOAD_DIR
        upload_path = Path(UPLOAD_DIR)
        matches = list(upload_path.glob(f"{req.file_id}.*"))
        if not matches:
            raise HTTPException(status_code=404, detail="Fichier uploadé introuvable ou expiré.")
        file_path = matches[0]
        ext = file_path.suffix.lower()

        # Déterminer le type d'outil à utiliser
        image_exts = {".png", ".jpg", ".jpeg", ".webp"}
        audio_exts = {".mp3", ".m4a", ".mp4", ".wav", ".mpeg"}
        pdf_exts = {".pdf"}

        if ext in image_exts:
            enriched_question = f"Analyse cette image : {file_path}\n\nConsigne de l'utilisateur : {req.question}"
            file_meta = {"type": "image", "path": str(file_path), "filename": file_path.name}
        elif ext in audio_exts:
            enriched_question = f"Transcris ce fichier audio : {file_path}\n\nConsigne de l'utilisateur : {req.question}"
            file_meta = {"type": "audio", "path": str(file_path), "filename": file_path.name}
        elif ext in pdf_exts:
            enriched_question = f"Analyse ce document PDF : {file_path}\n\nConsigne de l'utilisateur : {req.question}"
            file_meta = {"type": "pdf", "path": str(file_path), "filename": file_path.name}

    # Sauvegarder le message utilisateur (seulement si connecté)
    if user and conv_id:
        add_message(conv_id, "user", req.question)

    start_request(req.question)

    async def event_stream():
        import json as _json
        full_response = ""
        latency_ms = 0
        sources = None

        try:
            # Envoyer le conversation_id en premier événement
            start_data = {"type": "start", "conversation_id": conv_id}
            if file_meta:
                start_data["file"] = file_meta
            yield f"data: {_json.dumps(start_data)}\n\n"

            async for event in agent_react_stream(enriched_question, conversation_id=conv_id):
                # Vérifier la déconnexion client
                if await request.is_disconnected():
                    logger.info("[SSE] Client déconnecté.")
                    break

                if event["type"] == "done":
                    full_response = event.get("full_response", "")
                    latency_ms = event.get("latency_ms", 0)
                    sources = event.get("sources")

                yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            end_request(error=f"{type(exc).__name__}: {exc}")
            error_event = {"type": "error", "message": str(exc)}
            yield f"data: {_json.dumps(error_event, ensure_ascii=False)}\n\n"
            return

        end_request()

        # Sauvegarder la réponse en DB (seulement si connecté)
        message_id = None
        if user and conv_id and full_response:
            msg = add_message(conv_id, "assistant", full_response, latency_ms=latency_ms)
            message_id = msg["id"]

        # Envoyer le message_id au client pour le feedback
        if message_id or sources:
            meta_event = {"type": "meta"}
            if message_id:
                meta_event["message_id"] = message_id
            if sources:
                meta_event["sources"] = sources
            yield f"data: {_json.dumps(meta_event, ensure_ascii=False)}\n\n"

        # Générer un titre au 1er message
        if user and is_new and conv_id:
            title = _generate_title(req.question)
            update_conversation_title(conv_id, title)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Conversations endpoints (Phase 1 + Phase 2 user scoping)
# ---------------------------------------------------------------------------

@app.get("/conversations")
def conversations_list(request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Non authentifié.")
    return list_conversations(user_id=user["id"])


@app.get("/conversations/{conv_id}/messages")
def conversation_messages(conv_id: str, request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Non authentifié.")
    conv = get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return get_conversation_messages(conv_id)


@app.delete("/conversations/{conv_id}")
def conversation_delete(conv_id: str, request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Non authentifié.")
    if not delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return {"ok": True}


class ConversationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@app.patch("/conversations/{conv_id}")
def conversation_update(conv_id: str, req: ConversationUpdateRequest, request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Non authentifié.")
    if not update_conversation_title(conv_id, req.title):
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return {"ok": True, "title": req.title}


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
async def digest_page(request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(request, "digest.html", {"active_page": "digest", "user": user})


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


class ResponseFeedbackRequest(BaseModel):
    message_id: str
    rating: str = Field(..., pattern="^(up|down)$")
    comment: str | None = None


@app.post("/feedback/response")
@limiter.limit("30/minute")
def response_feedback(request: Request, req: ResponseFeedbackRequest, user=Depends(get_optional_user)):
    """Enregistre un feedback (thumbs up/down) sur une réponse de l'agent."""
    result = save_response_feedback(req.message_id, req.rating, req.comment)
    return result


@app.get("/feedback/stats")
def feedback_stats():
    """Stats globales des feedbacks sur les réponses."""
    return get_response_feedback_stats()


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
