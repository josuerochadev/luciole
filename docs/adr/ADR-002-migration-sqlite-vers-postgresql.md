# ADR-002 — Migration SQLite vers PostgreSQL (Neon)

**Date** : 2026-05-18
**Statut** : Accepté

---

## Contexte

Le projet utilisait SQLite pour trois usages distincts :
- Articles enrichis (`articles.json` + `data/luciole.db`)
- Conversations et messages utilisateurs
- Mémoire conversationnelle (`memory_conversations`)

Sur Railway (et Render), le système de fichiers est éphémère : toute donnée écrite
en dehors d'un volume persistant est perdue à chaque redéploiement. SQLite stockant
ses données dans un fichier local, toute la base était réinitialisée à chaque deploy.

## Décision

Migration vers **PostgreSQL hébergé sur Neon** (tier gratuit) pour toutes les tables
applicatives. La base SQLite de test (`data/test_clients.db`) est conservée uniquement
pour le démo ReAct (`query_db`).

**Tables migrées :**

| Table | Module |
|---|---|
| `articles`, `article_feedbacks` | `tools/database.py` |
| `users`, `conversations`, `messages`, `response_feedback` | `database.py` |
| `memory_conversations` | `memory/store.py` |

**Pattern de connexion standardisé :**
```python
def _pg_connect():
    return psycopg2.connect(os.getenv("DATABASE_URL"))
```

Les placeholders SQL sont passés de `?` (SQLite) à `%s` (PostgreSQL).
Les `INSERT OR IGNORE` sont remplacés par `INSERT ... ON CONFLICT (...) DO NOTHING`.

## Conséquences

**Positives :**
- Données persistantes entre les redéploiements Railway
- Accès concurrent supporté (plusieurs workers uvicorn)
- Neon offre un tier gratuit suffisant pour ce projet

**Négatives :**
- Latence réseau sur chaque requête DB (vs accès fichier SQLite)
- `DATABASE_URL` obligatoire en variable d'environnement
- Tests nécessitent un accès réseau (ou mocks) pour les opérations DB
