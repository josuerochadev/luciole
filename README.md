<div align="center">

# Luciole

**Agent IA de veille technologique — pipeline automatisé, RAG et interface conversationnelle.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?style=flat&logo=openai&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-enabled-2496ED?style=flat&logo=docker&logoColor=white)

[Documentation](docs/ARCHITECTURE.md) · [Portfolio](https://josuerocha.dev) · [Signaler un bug](https://github.com/josuerochadev/luciole/issues)

</div>

---

## À propos

Luciole est le projet fil rouge d'une formation de 70h consacrée à la conception et au déploiement d'agents IA (AJC Formation, 2025). L'objectif : automatiser la veille technologique en entreprise — collecte RSS, enrichissement par LLM, recherche sémantique et interface conversationnelle en langage naturel.

Projet réalisé en équipe avec Alex Dubus, Zhengfeng Ding et Stéphanie Consoli.

## Fonctionnalités

- **Pipeline automatisé** : collecte de ~40 flux RSS, filtrage thématique, enrichissement LLM (résumé, catégorie, score de pertinence 1-10)
- **Agent conversationnel ReAct** : raisonnement Reason → Act → Observe avec 7 outils (base de données, recherche web, RAG, email, scraping, transcription audio, analyse d'images)
- **RAG** : embeddings `text-embedding-3-small`, scoring hybride cosinus + fraîcheur, re-ranking optionnel via Cohere
- **Interface web** : chat avec streaming SSE, tableau de bord articles, mode sombre, upload fichiers, feedback sur les réponses
- **Auth** : comptes utilisateurs, authentification JWT
- **Rapports email** : digests HTML générés par LLM et envoyés par SMTP
- **Observabilité** : tracing LLM via Langfuse, métriques et KPIs (`/metrics`)
- **Gouvernance** : rétention automatique RGPD (90j articles, 30j logs), protection anti-injection, rate limiting

## Stack technique

| Catégorie | Outils |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| LLM | OpenAI API (gpt-4o-mini, gpt-4o, text-embedding-3-small) |
| RAG | numpy (cosinus), rank-bm25, Cohere re-ranking (optionnel) |
| Auth | python-jose (JWT), bcrypt |
| Observabilité | Langfuse, slowapi |
| Web & scraping | trafilatura, feedparser, Jinja2 |
| Déploiement | Docker, Render |

## Démarrer

### Prérequis

- Python 3.12+
- Clé API OpenAI

### Installation

```bash
git clone https://github.com/josuerochadev/luciole.git
cd luciole
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Renseigner OPENAI_API_KEY et API_KEY dans .env
```

### Lancer l'application

```bash
# Peuplement initial de la base d'articles
python pipeline.py

# Interface web + API (http://localhost:8000)
uvicorn api:app --reload

# Agent conversationnel en ligne de commande
python main.py
```

### Tests

```bash
python -m pytest tests/ -v
```

### Variables d'environnement

| Variable | Obligatoire | Description |
|---|---|---|
| `OPENAI_API_KEY` | oui | Clé API OpenAI |
| `API_KEY` | oui | Clé pour protéger les endpoints |
| `LANGFUSE_*` | non | Tracing LLM |
| `COHERE_API_KEY` | non | Re-ranking RAG |
| `SMTP_*` / `EMAIL_*` | non | Envoi de rapports email |

## Architecture

```
├── main.py              # Boucle ReAct (Reason → Act → Observe)
├── api.py               # API FastAPI
├── pipeline.py          # Pipeline RSS → LLM → stockage
├── llm.py               # Client OpenAI centralisé
├── config.py            # Configuration centralisée
├── security.py          # Rate limiting, headers sécurité
├── monitoring.py        # Métriques et KPIs
├── tracing.py           # Intégration Langfuse
├── tools/
│   ├── search.py        # Collecte RSS + recherche web
│   ├── database.py      # Persistance SQLite
│   ├── rag.py           # Embeddings + recherche sémantique
│   ├── email.py         # Génération et envoi de rapports HTML
│   ├── scraper.py       # Scraping web
│   ├── transcribe.py    # Transcription audio (Whisper)
│   └── vision.py        # Analyse d'images (GPT-4o)
├── memory/
│   └── store.py         # Mémoire de session conversationnelle
├── static/              # CSS/JS (design system Luciole)
├── templates/           # Templates Jinja2 (chat, dashboard, digest)
├── tests/               # Tests unitaires et d'intégration
├── docs/                # Documentation technique
├── Dockerfile
└── render.yaml
```

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour le détail des flux internes (pipeline, boucle ReAct, RAG, gardes-fous).

---

Construit par **[Josué Rocha](https://josuerocha.dev)** · [LinkedIn](https://linkedin.com/in/josuerocha) · [GitHub](https://github.com/josuerochadev)
