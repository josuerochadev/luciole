# =============================================================================
# Multi-stage Dockerfile — Agent de veille technologique (luciole_)
# =============================================================================
# Variables d'environnement requises au runtime :
#   API_KEY                 — Cle API pour authentifier les requetes (obligatoire)
#   OPENAI_API_KEY          — Cle API OpenAI (obligatoire)
#   SMTP_HOST               — Serveur SMTP (defaut: smtp.gmail.com)
#   SMTP_PORT               — Port SMTP (defaut: 587)
#   SMTP_PASSWORD            — Mot de passe SMTP
#   SMTP_USER               — Utilisateur SMTP
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
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install email-validator>=2.0.0 \
    && pip install --no-cache-dir --prefix=/install python-multipart>=0.0.9

# --------------- Stage 2 : prebuild (collecte RSS sans cle API) ---------------
FROM python:3.12-slim AS prebuild

WORKDIR /app

COPY --from=build /install /usr/local
COPY . .

# Collecte RSS + filtrage + scraping (pas besoin de cle API)
RUN python prebuild.py

# --------------- Stage 3 : runtime ---------------
FROM python:3.12-slim

WORKDIR /app

# Copier les packages Python installes depuis le stage build
COPY --from=build /install /usr/local

# Copier le code source
COPY . .

# Copier les articles pre-collectes depuis le stage prebuild
COPY --from=prebuild /app/data/articles_raw.json /app/data/articles_raw.json

# Utilisateur non-root pour la securite
RUN useradd --create-home --no-log-init appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["sh", "start.sh"]
