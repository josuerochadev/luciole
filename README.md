# Agent de Veille Technologique

Agent IA automatisé pour la veille technologique, développé dans le cadre d'une formation en Intelligence Artificielle.

## Fonctionnalités

- **Pipeline automatisé** : collecte d'articles RSS, filtrage par thèmes, enrichissement par LLM (résumé, catégorisation, score de pertinence)
- **Agent conversationnel** : interface en langage naturel avec raisonnement ReAct et 7 outils (base de données, recherche web, recherche sémantique, email, scraping, transcription audio, analyse d'images)
- **RAG (Retrieval-Augmented Generation)** : recherche sémantique par embeddings avec scoring hybride (similarité cosinus + fraîcheur)
- **Rapports email** : génération de digests HTML stylisés avec envoi SMTP
- **Gouvernance des données** : rétention automatique (90j articles, 30j logs), protection anti-injection SQL, conformité RGPD

## Architecture

```
fil-rouge/
├── main.py              # Agent conversationnel (boucle ReAct)
├── api.py               # API FastAPI (endpoints /ask, /digest, /feedback, etc.)
├── pipeline.py          # Pipeline automatisé RSS → LLM → stockage
├── seed.py              # Peuplement initial de la base d'articles
├── config.py            # Configuration centralisée
├── llm.py               # Interface OpenAI (appels LLM, parsing JSON)
├── security.py          # Middleware sécurité (rate limiting, headers)
├── monitoring.py        # Métriques et monitoring
├── tracing.py           # Intégration Langfuse (tracing LLM)
├── generate_traffic.py  # Génération de trafic pour tests de charge
├── tools/
│   ├── search.py        # Collecte RSS + recherche web
│   ├── database.py      # Persistance SQLite + JSON
│   ├── email.py         # Génération et envoi de rapports HTML
│   ├── rag.py           # Embeddings + recherche sémantique
│   ├── scraper.py       # Scraping de pages web
│   ├── transcribe.py    # Transcription audio (Whisper)
│   └── vision.py        # Analyse d'images (GPT-4o vision)
├── memory/
│   └── store.py         # Mémoire de session conversationnelle
├── static/              # Assets frontend
│   ├── luciole.css      # Design system Luciole
│   ├── luciole-chat.js  # Logique chat côté client
│   └── *.svg            # Favicon et wordmark
├── templates/           # Templates Jinja2
│   ├── base.html        # Layout principal
│   ├── index.html       # Interface chat
│   ├── dashboard.html   # Tableau de bord articles
│   ├── about.html       # Page à propos
│   └── digest.html      # Template email digest
├── tests/               # Tests unitaires et d'intégration
├── docs/                # Documentation technique
├── Dockerfile           # Image Docker de production
├── docker-compose.yml   # Orchestration Docker
├── render.yaml          # Configuration déploiement Render
├── start.sh             # Script de démarrage (pipeline au cold start)
└── data/                # Données générées (gitignored)
```

## Installation

```bash
# Cloner le repo
# Depuis la racine du repo
cd fil-rouge

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec votre clé OpenAI
```

## Utilisation

### Pipeline de veille (collecte et enrichissement)

```bash
python pipeline.py
```

### Agent conversationnel

```bash
python main.py
```

### Peuplement initial (articles de test)

```bash
python seed.py
```

### Tests

```bash
python -m pytest tests/ -v
```

## Configuration

Les paramètres principaux sont dans `config.py` :
- **Modèles LLM** : `gpt-4o-mini` (défaut), `gpt-4o` (vision/puissant) — température 0.3
- **Sources RSS** : ~40 flux (tech FR/EN, IA, cloud, cybersécurité, open source)
- **Thèmes surveillés** : ~60 mots-clés (IA, cloud, DevOps, sécurité, data...)
- **Seuil de pertinence** : 5/10 minimum

Variables d'environnement (voir `.env.example`) :
- `OPENAI_API_KEY` — clé API OpenAI (obligatoire)
- `API_KEY` — clé pour protéger les endpoints (obligatoire)
- `CORS_ORIGINS` — origines CORS autorisées
- `LANGFUSE_*` — observabilité LLM (optionnel)
- `COHERE_API_KEY` — re-ranking RAG (optionnel)
- `SMTP_*` / `EMAIL_*` — envoi de rapports email (optionnel)

## Équipe

Projet réalisé par **Alex Dubus**, **Zhengfeng Ding**, **Josue Xavier Rocha** et **Stéphanie Consoli**.

## Licence

Projet éducatif — usage libre.
