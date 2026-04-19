# Agent de Veille Technologique — Architecture et Fonctionnement

*Alex Dubus - Zhengfeng Ding - Josue Xavier Rocha - Stéphanie Consoli*

---

## 1. Le problème résolu

Les collaborateurs IT passent en moyenne **15 minutes par article × 2 articles par jour**, soit
**0,5h/jour de veille manuelle**. Sur 1 200 employés concernés, cela représente :

> **0,5 × 22 × 39,8€ × 1 200 × 12 ≈ 6,8 millions d'euros/an**

Le problème n'est pas seulement le coût — c'est que **la veille n'est souvent pas faite** par
manque de temps ou de priorité. L'agent automatise entièrement ce processus.

---

## 2. Vue d'ensemble

L'agent fonctionne selon deux modes complémentaires :

```
MODE PIPELINE (automatique, quotidien)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Internet        Agent                          Stockage
   │                                               │
   ├── Flux RSS ──► Filtrage ──► LLM ──► articles.json
   │                thèmes       résumé             │
   │                             catégorie ──► embeddings.json
   │                             pertinence

MODE CONVERSATIONNEL (à la demande, via ReAct)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Utilisateur ──► Question ──► LLM choisit un outil
                                  ├── query_db      (données structurées)
                                  ├── search_web    (actualités externes)
                                  ├── search_articles (archives sémantiques)
                                  └── réponse directe
                             ──► Exécution ──► Réponse finale
```

---

## 3. Architecture en couches

| Couche | Rôle | Fichiers |
|---|---|---|
| **1. Perception** | Lecture des flux RSS | `tools/search.py` |
| **2. Orchestration** | Pipeline quotidien + boucle ReAct | `pipeline.py`, `main.py` |
| **3. Raisonnement** | Résumé, catégorie, pertinence, choix d'outil | `llm.py` |
| **4. Mémoire** | Articles archivés, embeddings, historique session | `memory/store.py`, `data/` |
| **5. Outils** | Base de données, recherche web, RAG | `tools/` |
| **6. Gouvernance** | Anti-hallucination, limite boucle, rétention RGPD | `main.py`, `tools/database.py` |
| **7. Sortie** | JSON enrichi, réponses conversationnelles | `data/articles.json` |

---

## 4. Le pipeline quotidien (`pipeline.py`)

C'est le cœur de l'automatisation. Il s'exécute en 4 étapes séquentielles :

```
┌─────────────────────────────────────────────────────────────┐
│ ÉTAPE 1 — Collecte RSS                                       │
│ recuperer_articles_rss()                                     │
│ Lit tous les flux configurés (next.ink, 4sysops, AWS blog…) │
│ → 200-300 articles bruts par exécution                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ ÉTAPE 2 — Filtrage thématique                                │
│ filtrer_par_theme()                                          │
│ Garde uniquement les articles contenant les mots-clés        │
│ (IA, cloud, cybersécurité, kubernetes, GPU…)                 │
│ → ~50% des articles conservés                                │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ ÉTAPE 3 — Enrichissement LLM                                 │
│ resumer_article()  →  appeler_llm_json()                     │
│ Pour chaque nouvel article, le LLM génère :                  │
│   • resume    : synthèse en 2-3 phrases                      │
│   • categorie : IA | Cloud | Cybersécurité | …               │
│   • pertinence: score 1-10                                   │
│   • action    : lire | archiver | ignorer                    │
│ Les articles < seuil (pertinence < 5) sont ignorés           │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ ÉTAPE 4 — Sauvegarde + Indexation RAG                        │
│ sauvegarder_articles()  +  indexer_articles()                │
│ • articles.json     : données structurées (SQL-like)         │
│ • embeddings.json   : vecteurs pour la recherche sémantique  │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. La boucle ReAct (`main.py`)

ReAct = **Re**ason + **Act**. C'est le pattern qui donne à l'agent sa capacité à raisonner
avant d'agir.

```
Question utilisateur : "Quels articles on a sur les failles Kubernetes ?"
         │
         ▼
┌─────────────────────────────────────────────┐
│ REASON — choisir_outil()                     │
│                                             │
│ Le LLM reçoit la question + le schéma       │
│ des outils disponibles et répond en JSON :  │
│ {                                           │
│   "intent": "rag",                          │
│   "outil": "search_articles",               │
│   "query_recherche": "failles Kubernetes",  │
│   "raisonnement": "question sur archives"   │
│ }                                           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ ACT — executer_outil()                        │
│                                              │
│ Dispatch selon l'outil choisi :              │
│                                              │
│  query_db       → SQLite (données clients)   │
│  search_web     → banque d'articles simulés  │
│  search_articles→ recherche sémantique RAG ◄─┤
│  réponse_directe→ aucun outil                │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ OBSERVE — formuler_reponse()                  │
│                                              │
│ Le LLM reçoit la question initiale +         │
│ le résultat de l'outil et formule une        │
│ réponse en langage naturel.                  │
│                                              │
│ Si l'outil a retourné [ERREUR_OUTIL] :       │
│ → instruction anti-hallucination activée     │
└──────────────────────────────────────────────┘
```

**Garde contre les boucles** : si le même outil est choisi deux fois de suite,
l'agent bascule en réponse directe plutôt que de boucler indéfiniment.

---

## 6. Le RAG (`tools/rag.py`)

RAG = **R**etrieval-**A**ugmented **G**eneration.

### Pourquoi ça fonctionne

Un LLM seul ne connaît pas vos articles. Le RAG lui donne accès à votre base de
connaissance privée en 2 temps :

```
PHASE D'INDEXATION (une fois par article)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Article (titre + résumé)
        │
        ▼
API OpenAI text-embedding-3-small
        │
        ▼
Vecteur de 1536 dimensions   ←── représentation mathématique du sens
        │
        ▼
embeddings.json  {id, vecteur, métadonnées}


PHASE DE RECHERCHE (à chaque question)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Question utilisateur
        │
        ▼
API OpenAI  →  vecteur de la question
        │
        ▼
Similarité cosine avec tous les vecteurs de la base
        │
        ▼
Top N articles les plus proches sémantiquement
        │
        ▼
Injectés dans le prompt → LLM génère une réponse contextualisée
```

### Pourquoi la similarité cosine

Deux textes qui parlent du même sujet ont des vecteurs qui "pointent dans la même
direction" dans l'espace à 1536 dimensions, même si les mots exacts sont différents.

> *"Startups européennes qui lèvent des fonds"* → retrouve l'article
> *"Mistral AI lève 600M€"* avec un score de 0.51, sans aucun mot en commun.

---

## 7. La gestion de la mémoire

L'agent a deux types de mémoire distincts :

| Type | Implémentation | Durée | Usage |
|---|---|---|---|
| **Session** | `deque(maxlen=10)` en RAM | Le temps d'une conversation | Contexte conversationnel |
| **Long terme** | `articles.json` + `embeddings.json` | 90 jours (RGPD) | Base de connaissance RAG |

La mémoire de session permet des échanges cohérents :
```
User : "Je m'appelle Alice"
User : "Comment je m'appelle ?"
Agent: "Vous vous appelez Alice."   ← grâce aux 10 derniers messages en mémoire
```

---

## 8. Les gardes-fous

| Problème | Solution implémentée |
|---|---|
| **Hallucination** | Préfixe `[ERREUR_OUTIL]` + instruction LLM "n'invente aucun chiffre" |
| **Boucle infinie** | `MAX_ITERATIONS = 2` + tracking des outils déjà essayés |
| **Intent incorrect** | System prompt enrichi avec exemples métier détaillés |
| **Texte trop long** | Troncature à 3 000 caractères avant embedding |
| **Fuite de données** | Clé API en variable d'environnement, `.env` dans `.gitignore` |
| **Rétention RGPD** | Purge automatique à 90 jours (articles) et 30 jours (logs) |

---

## 9. Structure des fichiers

```
fil-rouge/
│
├── config.py          → paramètres globaux (modèle, sources RSS, thèmes, RGPD)
├── llm.py             → appeler_llm(), appeler_llm_json(), resumer_article()
├── pipeline.py        → pipeline quotidien RSS → LLM → stockage
├── main.py            → boucle ReAct interactive
├── api.py             → API FastAPI (endpoints /ask, /digest, /feedback, etc.)
├── security.py        → middleware sécurité (rate limiting, headers)
├── monitoring.py      → métriques et monitoring
├── tracing.py         → intégration Langfuse (tracing LLM)
├── seed.py            → peuplement initial de la base d'articles
├── generate_traffic.py → génération de trafic pour tests de charge
│
├── tools/
│   ├── search.py      → recuperer_articles_rss(), search_web()
│   ├── database.py    → sauvegarder_articles(), query_db() SQLite
│   ├── rag.py         → indexer_article(), rechercher_articles()
│   ├── email.py       → génération et envoi de rapports HTML
│   ├── scraper.py     → scraping de pages web
│   ├── transcribe.py  → transcription audio (Whisper)
│   └── vision.py      → analyse d'images (GPT-4o vision)
│
├── memory/
│   └── store.py       → store(), recall(), clear() — mémoire conversationnelle
│
├── static/            → assets frontend (design system Luciole)
│   ├── luciole.css        CSS du design system
│   ├── luciole-chat.js    logique chat côté client
│   └── *.svg              favicon et wordmark
│
├── templates/         → templates Jinja2
│   ├── base.html          layout principal
│   ├── index.html         interface chat
│   ├── dashboard.html     tableau de bord articles
│   ├── about.html         page à propos
│   └── digest.html        template email digest
│
├── tests/             → tests unitaires et d'intégration
│
├── Dockerfile         → image Docker de production
├── docker-compose.yml → orchestration Docker
├── render.yaml        → configuration déploiement Render
├── start.sh           → script de démarrage (pipeline au cold start)
│
├── data/              → généré automatiquement
│   ├── articles.json      articles enrichis (90j)
│   ├── embeddings.json    vecteurs RAG
│   ├── archives.json      articles archivés
│   ├── logs.jsonl         logs structurés (30j)
│   ├── test_clients.db    base SQLite de test
│   └── historique_envois.json
│
└── docs/              → documentation technique
    ├── ARCHITECTURE.md    ce fichier
    └── ROADMAP-UX.md      roadmap UX/UI
```

---

## 10. Flux complet d'une question

```
"Quels sont les risques de sécurité liés aux LLMs cette semaine ?"

    [1] main.py → choisir_outil()
        LLM → { intent: "rag", outil: "search_articles",
                query_recherche: "risques sécurité LLM" }

    [2] main.py → executer_outil()
        RAG → embedding de "risques sécurité LLM"
            → similarité cosine sur 213 articles
            → top 5 : prompt injection (0.71), red teaming IA (0.65),
                       deepfake audio (0.58), OWASP API (0.54), NIS2 (0.51)

    [3] main.py → formuler_reponse()
        LLM reçoit : question + 5 articles contextuels
        LLM génère : réponse structurée en français avec les tendances
                     de la semaine issues de votre base de veille
```

---

## 11. État des fonctionnalités

| Fonctionnalité | Statut |
|---|---|
| Envoi email quotidien | Implémenté (`tools/email.py`, SMTP) |
| Interface utilisateur web | Implémenté (FastAPI + templates Jinja2 + design system Luciole) |
| Pipeline automatisé au démarrage | Implémenté (`start.sh`) |
| Observabilité LLM (Langfuse) | Implémenté (`tracing.py`) |
| Déploiement Docker / Render | Implémenté (`Dockerfile`, `render.yaml`) |
| Outils multimodaux (audio, vision) | Implémenté (`tools/transcribe.py`, `tools/vision.py`) |
| Historique de conversations persistant | À implémenter (voir `docs/ROADMAP-UX.md` Phase 1) |
| Comptes utilisateurs | À implémenter (voir `docs/ROADMAP-UX.md` Phase 2) |
| Streaming des réponses (SSE) | À implémenter (voir `docs/ROADMAP-UX.md` Phase 3) |
| Traduction des articles EN → FR | Hors périmètre |
| Réseaux sociaux (Twitter/LinkedIn) | Hors périmètre |
