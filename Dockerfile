# =============================================================================
# Multi-stage Dockerfile — Agent de veille technologique (luciole_)
# =============================================================================
# Variables d'environnement requises au runtime :
#   OPENAI_API_KEY          — Cle API OpenAI (obligatoire)
#   SMTP_HOST               — Serveur SMTP (defaut: smtp.gmail.com)
#   SMTP_PORT               — Port SMTP (defaut: 587)
#   SMTP_USER               — Utilisateur SMTP
#   SMTP_PASSWORD            — Mot de passe SMTP
#   EMAIL_EXPEDITEUR        — Adresse expediteur (defaut: veille@example.com)
#   EMAIL_DESTINATAIRES     — Adresses destinataires, separees par des virgules
#   LANGFUSE_PUBLIC_KEY     — Cle publique Langfuse (optionnel, tracing)
#   LANGFUSE_SECRET_KEY     — Cle secrete Langfuse (optionnel, tracing)
#   TAVILY_API_KEY          — Cle API Tavily (optionnel, recherche web)
# =============================================================================

# --------------- Stage 1 : build (installation des dependances) ---------------
FROM python:3.12-slim AS build

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --------------- Stage 2 : runtime ---------------
FROM python:3.12-slim

WORKDIR /app

# Copier les packages Python installes depuis le stage build
COPY --from=build /install /usr/local

# Copier le code source
COPY . .

# Creer le dossier data (utilise au runtime pour articles, logs, archives)
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
