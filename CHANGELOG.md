# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [Unreleased]

---

## [1.2.0] — 2026-05-18

### Modifié
- Migration LLM : OpenAI (gpt-4o) → Google Gemini (gemini-2.5-flash / gemini-2.5-pro)
- Migration embeddings : text-embedding-3-small → gemini-embedding-001
- Transcription audio désactivée (dépendance Whisper supprimée)

### Infrastructure
- Migration base de données : SQLite → PostgreSQL (Neon)
- Migration hébergement : Render → Railway (`railway.toml`)
- Mise à jour des variables d'environnement Dockerfile (`GEMINI_API_KEY`, `DATABASE_URL`)

### Documentation
- Réécriture du README (stack, onboarding, variables d'env)
- Ajout `TAVILY_API_KEY` dans `.env.example`

---

## [1.1.0] — 2026-04-20

### Ajouté
- **Phase 6** : feedback utilisateur (pouce haut/bas + commentaire) sur les réponses de l'agent
- **Phase 6** : affichage des sources RAG utilisées sous chaque réponse
- Fiabilité agent : 10 corrections anti-hallucination, isolation mémoire par conversation, performance

### Corrigé
- Dépendance `python-multipart` manquante pour l'upload de fichiers
- Nettoyage nav : déduplication du nom utilisateur, suppression des bordures de bouton

---

## [1.0.0] — 2026-04-19

### Ajouté
- **Phase 5** : dark mode avec détection `prefers-color-scheme` + bascule manuelle (localStorage)
- **Phase 4** : upload de fichiers dans le chat (drag & drop, validation magic bytes, TTL 1h)
- **Phase 3** : streaming des réponses en temps réel via Server-Sent Events (SSE)
- **Phase 2** : comptes utilisateurs — inscription/connexion, JWT (cookie httpOnly), bcrypt
- **Phase 1** : historique des conversations persistant (SQLite → PostgreSQL), sidebar, titres auto
- **Phase 0** : renommage du design system Pulse → Luciole
- Cascade de modèles : classification simple/complexe pour optimiser les coûts LLM
- Reranking Cohere (optionnel) pour le RAG
- Script `prebuild.py` : collecte RSS au build Docker (cold start optimisé)
- Tracing Langfuse (`tracing.py`) avec décorateurs `@observe`

### Sécurité
- Auth JWT + rate limiting (slowapi) + headers sécurité
- Conteneur Docker non-root
- CORS configurable

### Infrastructure
- Déploiement Docker multi-stage sur Render (puis migré Railway en v1.2.0)
- Health check sur `/health`

---

## [0.3.0] — 2026-04-17

### Ajouté
- RAG hybride v3 : BM25 + similarité cosine + fraîcheur + chunking (500 mots, overlap 80)
- HyDE (Hypothetical Document Embeddings) pour l'expansion de requête
- Boost RAG par feedback utilisateur (+10% si note ≥ 8)
- Cache LRU pour les embeddings de requêtes
- Outils email (`tools/email.py`) : génération HTML + envoi SMTP
- Mémoire conversationnelle persistante
- Monitoring (`/metrics`) : tokens, latence P95, coût estimé, taux de fallback
- Interface web complète : chat SSE, dashboard articles, page about, digest

### Corrigé
- Fix 403 sur Render : support header `X-Forwarded-Host` pour reverse proxy
- Réduction batch embeddings pour éviter la limite 300k tokens OpenAI

---

## [0.2.0] — 2026-04-17

### Ajouté
- Agent ReAct complet : `choisir_outil` → `executer_outil` → `formuler_reponse`
- Function calling natif pour la décision d'outil
- Gardes-fous : `MAX_ITERATIONS = 2`, détection boucle, marqueurs `[ERREUR_OUTIL]`
- Pipeline enrichi : scraping `trafilatura`, déduplication par similarité de titre (seuil 0.85), enrichissement LLM parallèle (5 workers)
- Outil `query_db` : SQLite de test (`test_clients.db`)
- Outil `search_web` : Tavily API avec fallback gracieux
- Outil `analyze_image` : Gemini Vision (PNG, JPEG, WebP, PDF)
- Sécurité : validation anti-injection prompt/SQL, filtrage des sorties (IBAN, CB, email)
- Suite de tests : 15+ fichiers couvrant agent, RAG, auth, streaming, sécurité, email

---

## [0.1.0] — 2026-04-17

### Ajouté
- Pipeline RSS initial : collecte (~40 flux), filtrage thématique, enrichissement LLM (résumé, catégorie, pertinence 1-10)
- RAG v1 : embeddings + similarité cosine numpy
- Digest email HTML avec APScheduler (exécution quotidienne configurable)
- API FastAPI minimale : `POST /ask`, `GET /health`
- Containerisation Docker
