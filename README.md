<div align="center">

# Luciole

**Agent IA de veille technologique — pipeline automatisé, RAG et interface conversationnelle.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-API-4285F4?style=flat&logo=google&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-deployed-0B0D0E?style=flat&logo=railway&logoColor=white)

[**Démo live**](https://luciole-production.up.railway.app) · [Documentation](docs/ARCHITECTURE.md) · [Portfolio](https://josuerocha.dev) · [Signaler un bug](https://github.com/josuerochadev/luciole/issues)

</div>

---

## À propos

Luciole est le projet fil rouge d'une formation de 70h consacrée à la conception et au déploiement d'agents IA (AJC Formation, 2025). L'objectif : automatiser la veille technologique en entreprise — collecte RSS, enrichissement par LLM, recherche sémantique et interface conversationnelle en langage naturel.

Projet réalisé en équipe avec Alex Dubus, Zhengfeng Ding et Stéphanie Consoli.

## Fonctionnalités

- **Pipeline automatisé** : collecte de ~40 flux RSS, filtrage thématique, enrichissement LLM (résumé, catégorie, score de pertinence 1-10)
- **Agent conversationnel ReAct** : raisonnement Reason → Act → Observe avec 6 outils (base de données, recherche web, RAG, email, scraping, analyse d'images)
- **RAG** : embeddings `gemini-embedding-001`, scoring hybride cosinus + fraîcheur, re-ranking optionnel via Cohere
- **Interface web** : chat avec streaming SSE, tableau de bord articles, mode sombre, upload fichiers, feedback sur les réponses
- **Auth** : comptes utilisateurs, authentification JWT
- **Rapports email** : digests HTML générés par LLM et envoyés par SMTP
- **Observabilité** : tracing LLM via Langfuse, métriques et KPIs (`/metrics`)
- **Gouvernance** : rétention automatique RGPD (90j articles, 30j logs), protection anti-injection, rate limiting

## Stack technique

| Catégorie | Outils |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| LLM | Google Gemini API (gemini-2.5-flash, gemini-2.5-pro, gemini-embedding-001) |
| RAG | numpy (cosinus), rank-bm25, Cohere re-ranking (optionnel) |
| Base de données | PostgreSQL (Neon) |
| Auth | python-jose (JWT), bcrypt |
| Observabilité | Langfuse, slowapi |
| Web & scraping | trafilatura, feedparser, Jinja2 |
| Déploiement | Docker, Railway |

## Démarrer

### Prérequis

- Python 3.12+
- Clé API Gemini (Google AI Studio — gratuit)
- Base PostgreSQL (Neon — gratuit)

### Installation

```bash
git clone https://github.com/josuerochadev/luciole.git
cd luciole
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Renseigner GEMINI_API_KEY, DATABASE_URL et API_KEY dans .env
```

### Lancer l'application

```bash
# Initialisation de la base + peuplement initial des articles
# (crée les tables PostgreSQL et importe les premiers articles)
python startup.py

# Interface web + API (http://localhost:8000)
uvicorn api:app --reload

# Agent conversationnel en ligne de commande
python main.py
```

> **Note :** les tables PostgreSQL sont créées automatiquement au premier démarrage. Si la base est vide, `startup.py` lance le pipeline RSS complet. Pour un peuplement rapide avec des données de démonstration, utiliser `python seed.py`.

### Tests

```bash
python -m pytest tests/ -v
```

### Variables d'environnement

| Variable | Obligatoire | Description |
|---|---|---|
| `GEMINI_API_KEY` | oui | Clé API Google Gemini |
| `DATABASE_URL` | oui | URL PostgreSQL Neon |
| `API_KEY` | oui | Clé pour protéger les endpoints |
| `JWT_SECRET` | oui | Secret pour les tokens d'authentification |
| `TAVILY_API_KEY` | recommandé | Recherche web temps réel |
| `LANGFUSE_*` | non | Tracing LLM (Langfuse cloud) |
| `COHERE_API_KEY` | non | Re-ranking RAG (Cohere) |
| `SMTP_*` / `EMAIL_*` | non | Envoi de rapports email |
| `CORS_ORIGINS` | non | Origines CORS autorisées (virgule si plusieurs) |
| `VEILLE_HEURE` | non | Heure du pipeline automatique (défaut : `08:00`) |

## Architecture

```
├── main.py              # Boucle ReAct (Reason → Act → Observe)
├── api.py               # API FastAPI
├── pipeline.py          # Pipeline RSS → LLM → stockage
├── llm.py               # Client Gemini centralisé (compat OpenAI)
├── config.py            # Configuration centralisée
├── database.py          # Persistance PostgreSQL (conversations, auth)
├── security.py          # Rate limiting, headers sécurité
├── monitoring.py        # Métriques et KPIs
├── tracing.py           # Intégration Langfuse
├── tools/
│   ├── search.py        # Collecte RSS + recherche web
│   ├── database.py      # Persistance PostgreSQL (articles, feedbacks)
│   ├── rag.py           # Embeddings + recherche sémantique
│   ├── email.py         # Génération et envoi de rapports HTML
│   ├── scraper.py       # Scraping web
│   └── vision.py        # Analyse d'images (Gemini Vision)
├── memory/
│   └── store.py         # Mémoire de session conversationnelle (PostgreSQL)
├── static/              # CSS/JS (design system Luciole)
├── templates/           # Templates Jinja2 (chat, dashboard, digest)
├── tests/               # Tests unitaires et d'intégration
├── docs/                # Documentation technique
├── Dockerfile
└── railway.toml
```

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour le détail des flux internes (pipeline, boucle ReAct, RAG, gardes-fous).

---

Construit par **[Josué Rocha](https://josuerocha.dev)** · [LinkedIn](https://linkedin.com/in/josuerocha) · [GitHub](https://github.com/josuerochadev)
