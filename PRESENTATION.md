# Luciole — Agent IA de Veille Technologique

> Projet fil rouge — Formation "Concevoir, developper et deployer un agent IA sur mesure"

---

## Vue d'ensemble

**Luciole** est un agent conversationnel intelligent specialise dans la veille technologique. Il collecte, analyse et restitue l'actualite tech (IA, cybersecurite, cloud, DevOps, data, open source) via une interface de chat en temps reel.

**Ce qui le distingue** : ce n'est pas un simple chatbot. C'est un systeme complet qui combine un pipeline automatise de collecte d'articles, un moteur de recherche semantique (RAG), et un agent ReAct capable de raisonner et d'utiliser des outils pour repondre aux questions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      UTILISATEUR                            │
│                  (navigateur web)                           │
└──────────────┬──────────────────────────────────────────────┘
               │ SSE (streaming temps reel)
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    API FastAPI                               │
│  /ask  /auth  /conversations  /upload  /metrics  /digest    │
│  Authentification JWT · Rate limiting · CORS                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                  AGENT ReAct (main.py)                       │
│         REASON  ──►  ACT  ──►  OBSERVE                      │
│                                                              │
│  1. Classifie la requete (simple/complexe)                   │
│  2. Choisit un outil via function calling                    │
│  3. Execute l'outil                                          │
│  4. Formule une reponse fidelement                           │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┼───────┬───────┬───────┬───────┬───────┐
       ▼       ▼       ▼       ▼       ▼       ▼       ▼
   ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
   │ RAG  ││Search││  DB  ││Audio ││Vision││Digest││Email │
   │      ││ Web  ││SQLite││Whisp.││GPT-4o││      ││ SMTP │
   └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘
```

### Pattern ReAct : Reason → Act → Observe

L'agent suit un cycle de raisonnement en 3 etapes :

1. **Reason** — Le LLM analyse la question, evalue sa complexite (cascade simple/complexe), et choisit l'outil le plus adapte via function calling
2. **Act** — L'outil selectionne est execute (recherche RAG, requete SQL, appel API, transcription audio...)
3. **Observe** — Le resultat est reformule en langage naturel avec des regles strictes anti-hallucination

Protection contre les boucles infinies : maximum 2 iterations, detection de repetition d'outil → fallback automatique.

---

## Fonctionnalites implementees

### 1. Pipeline de veille automatise

```
40+ flux RSS  →  Filtrage thematique  →  Deduplication  →  Scraping contenu
                                                                   │
Email digest  ←  Stockage SQLite + RAG  ←  Enrichissement LLM  ←──┘
```

- **Collecte** : 40+ sources RSS (Korben, ZDNet, OpenAI blog, HackerNews, AWS...)
- **Filtrage** : Conservation des articles tech uniquement (mots-cles IA, cloud, cyber...)
- **Deduplication** : Par URL + similarite de titre (seuil 0.85)
- **Enrichissement LLM** : Resume, categorisation (8 categories), score de pertinence (1-10), traitement parallele (5 workers)
- **Indexation** : Stockage SQLite + embeddings pour recherche semantique
- **Digest email** : Rapport HTML avec articles classes par categorie, envoye par SMTP
- **Planification** : Execution quotidienne configurable (defaut 08h00)

### 2. RAG hybride (Retrieval-Augmented Generation)

Le moteur de recherche combine 3 signaux pour trouver les articles les plus pertinents :

| Signal | Poids | Methode |
|--------|-------|---------|
| Semantique | 50% | Similarite cosinus (text-embedding-3-small) |
| Lexical | 25% | BM25 (correspondance de termes) |
| Fraicheur | 25% | Decroissance lineaire sur 90 jours |

Fonctionnalites avancees :
- **HyDE** (Hypothetical Document Embeddings) : expansion de requete pour un meilleur rappel
- **Reranking Cohere** (optionnel) : reordonnancement multilingual
- **Boost par feedback** : +10% si l'article a ete note 8+/10 par un utilisateur
- **Deduplication** : Regroupement par article (pas par chunk)
- **Cache** : LRU pour les embeddings, invalidation par mtime pour l'index
- **Chunking** : Decoupage en blocs de 500 mots avec chevauchement de 80 mots

### 3. Capacites multimodales

- **Transcription audio** : Whisper API (MP3, WAV, M4A, WebM, FLAC...) avec analyse automatique (resume, points cles, niveau de formalite)
- **Analyse d'images** : GPT-4o Vision (PNG, JPEG, WebP) avec extraction structuree JSON
- **Lecture de PDF** : Conversion premiere page en image + analyse Vision
- **Upload de fichiers** : Drag & drop, validation par magic bytes, limite 10 Mo, nettoyage auto (TTL 1h)

### 4. Authentification et persistance

- **Inscription/connexion** : Hashage bcrypt + tokens JWT (cookie httpOnly)
- **Historique** : Conversations et messages persistes en SQLite par utilisateur
- **Sidebar** : Liste des conversations, renommage, suppression
- **Titre auto** : Generation du titre de conversation par LLM au premier message

### 5. Streaming temps reel (SSE)

L'interface affiche les reponses en temps reel via Server-Sent Events :
- Visualisation de la reflexion de l'agent ("outil selectionne", "recherche en cours...")
- Affichage chunk par chunk de la reponse
- Indicateur de latence (ms)

### 6. Systeme de feedback

- **Feedback sur les reponses** : Pouce haut/bas + commentaire optionnel
- **Feedback sur les articles** : Note 1-10 (influence le score RAG)
- **Statistiques** : Taux de satisfaction global, accessible via `/feedback/stats`
- **Sources RAG** : Affichage des articles utilises pour generer la reponse

---

## Securite

### Validation des entrees
- Longueur max : 2000 caracteres
- Detection d'injection de prompt (regex : "ignore all instructions", "show system prompt", "jailbreak"...)
- Prevention d'injection SQL (seul SELECT autorise, blocage de DROP/DELETE/UPDATE/UNION...)
- Blocage d'actions non autorisees ("send email to all", "delete all data"...)

### Filtrage des sorties
Les donnees sensibles sont automatiquement masquees dans les reponses :
- IBAN → `[IBAN MASQUE]`
- Carte bancaire → `[CB MASQUE]`
- Email → `[EMAIL MASQUE]`
- Telephone → `[TEL MASQUE]`

### Protection API
- Rate limiting (slowapi) : 5-20 requetes/minute selon l'endpoint
- Authentification par cle API (X-API-Key) + JWT utilisateur
- CORS configure (origines autorisees)

---

## Anti-hallucination

Un effort particulier a ete porte sur la fiabilite des reponses :

1. **Regles strictes** dans les prompts : "Ne jamais inventer de titres, URLs, dates ou statistiques"
2. **Marqueurs d'erreur explicites** : `[ERREUR_OUTIL]`, `[AUCUN_RESULTAT]`, `[ERREUR_SECURITE]`
3. **Instruction de transparence** : Si l'outil echoue → "Je n'ai pas pu trouver cette information" (pas d'invention)
4. **Annonce proactive** : Si moins de resultats que demande → "J'ai trouve 3 resultats sur les 5 demandes"
5. **Clarification** : En cas d'ambiguite → proposition de 2 interpretations

---

## Observabilite

### Monitoring (`/metrics`)
- Nombre total de requetes, duree moyenne et P95
- Tokens consommes (prompt + completion)
- Estimation du cout en USD (tarification gpt-4o-mini)
- Taux d'erreur et taux de fallback
- Historique des dernieres requetes (`/metrics/recent`)

### Tracing (Langfuse)
- Instrumentation optionnelle des appels LLM
- Spans par fonction (`@observe()`)
- Scoring qualite sur les traces

### KPI frontend
- Affichage en temps reel dans l'interface : nombre de requetes, latence, taux d'erreur

---

## Interface utilisateur

### Design system "Luciole"
- **Dark mode** : Detection automatique des preferences systeme + bascule manuelle (localStorage)
- **Responsive** : Mobile-first, breakpoint 768px, sidebar retractable
- **Composants** : Bulles de message, indicateur de saisie (3 points animes), previsualisations de fichiers, badges d'attachement
- **Rendu Markdown** : Rendu en temps reel dans les messages (via marked.js)

### Pages
| Page | Description |
|------|-------------|
| `/` | Interface de chat principale |
| `/login` | Inscription et connexion |
| `/dashboard` | Historique des conversations |
| `/about` | Presentation de l'agent et ses capacites |
| `/digest-page` | Visualisation du digest avec statistiques |

---

## Optimisations de performance

- **Cascade de modeles** : Classification rapide (simple → gpt-4o-mini, complexe → gpt-4o) pour reduire les couts
- **Embeddings en batch** : Jusqu'a 100 textes par appel API
- **Cache LRU** : Embeddings de requetes mis en cache
- **Cache memoire** : Index RAG + BM25 charges une seule fois, invalides par mtime
- **Enrichissement parallele** : ThreadPool de 5 workers pour le traitement des articles
- **Fallbacks gracieux** : Tavily indisponible → resultats vides ; Langfuse absent → pas de tracing ; JSON invalide → extraction regex

---

## Deploiement

### Docker (multi-stage)
```
Stage 1 (build)    →  Installation des dependances
Stage 2 (prebuild) →  Collecte RSS initiale (sans cle API)
Stage 3 (runtime)  →  Python 3.12-slim, utilisateur non-root, health check
```

### Hebergement : Render.com
- Service web Docker, region Frankfurt, plan free
- Variables d'environnement configurees (API keys, CORS)
- Health check sur `/health`
- Cold start : execution du pipeline au demarrage (`start.sh`)

---

## Tests

Suite de **15+ fichiers de tests** couvrant l'ensemble du systeme :

| Module | Tests |
|--------|-------|
| Authentification | Inscription, login, JWT, hashage bcrypt |
| Conversations | Creation, chargement, liste, suppression |
| Agent ReAct | Flux end-to-end complet |
| RAG | Recherche semantique, chunking, embeddings, deduplication |
| Streaming | SSE, visualisation des outils |
| Memoire | Stockage/rappel de session |
| Feedback | Retour reponse, notation article |
| Securite | Injection prompt, injection SQL, actions non autorisees |
| Email | Generation HTML, envoi SMTP |
| Integration | Pipeline complet |
| Qualite | Qualite des reponses, detection d'hallucination |
| Dark mode | Bascule frontend |
| Upload | Validation fichiers, magic bytes |
| JSON parsing | Strategies de fallback |

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| LLM | OpenAI API (gpt-4o-mini, gpt-4o) |
| Embeddings | text-embedding-3-small |
| Framework web | FastAPI + uvicorn |
| Base de donnees | SQLite (WAL mode) |
| RAG | numpy (cosinus) + BM25 + Cohere reranking |
| Auth | bcrypt + JWT (python-jose) |
| Audio | Whisper API |
| Vision | GPT-4o Vision |
| Recherche web | Tavily API |
| Email | smtplib (SMTP TLS) |
| Scraping | trafilatura + feedparser |
| Observabilite | Langfuse |
| Frontend | Jinja2 + CSS/JS custom |
| Deploiement | Docker + Render |
| Tests | pytest |
| Python | 3.12+ |

---

## Variables d'environnement

| Variable | Obligatoire | Description |
|----------|:-----------:|-------------|
| `OPENAI_API_KEY` | Oui | Acces API OpenAI |
| `API_KEY` | Oui | Authentification API FastAPI |
| `JWT_SECRET` | Non | Secret JWT (auto-genere si absent) |
| `TAVILY_API_KEY` | Non | Recherche web (fallback gracieux) |
| `LANGFUSE_*_KEY` | Non | Tracing LLM |
| `COHERE_API_KEY` | Non | Reranking RAG |
| `SMTP_*` | Non | Configuration email |
| `VEILLE_HEURE` | Non | Heure du pipeline (defaut 08:00) |
| `CORS_ORIGINS` | Non | Origines CORS autorisees |

---

## Commandes

```bash
# Lancer l'agent en mode CLI
python main.py

# Lancer l'API
uvicorn api:app --reload

# Executer le pipeline de veille
python pipeline.py
python pipeline.py --dry-run     # Sans envoi d'email
python pipeline.py --schedule    # Mode planifie (quotidien)

# Lancer les tests
python -m pytest tests/

# Build Docker
docker build -t luciole .
docker run -p 8000:8000 --env-file .env luciole
```

---

*Projet realise dans le cadre de la formation AJC — "Concevoir, developper et deployer un agent IA sur mesure"*
