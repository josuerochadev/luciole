# Exercice 3 — Implémenter un agent ReAct minimal

*Alex Dubus - Zhengfeng Ding - Josue Xavier Rocha - Stéphanie Consoli*

---

## Étape 1 — 2 tools implémentés

### `tools/search.py` — `search_web(query)`

Simule une recherche web avec une banque de résultats fictifs organisée par mots-clés thématiques (IA, GPU, Cloud, Cybersécurité). Retourne une liste de dicts `{titre, url, extrait}`.

```python
def search_web(query: str) -> list[dict]:
    # Correspond la query à une banque de résultats par mots-clés
    # Retourne un résultat générique si aucun mot-clé ne correspond
```

### `tools/database.py` — `query_db(sql)`

Interroge une base SQLite locale (`data/test_clients.db`) initialisée avec 3 clients fictifs :

| id | nom | email | type | depuis |
|---|---|---|---|---|
| 1 | Alice Martin | alice.martin@example.com | Premium | 2023-01-15 |
| 2 | Bob Dupont | bob.dupont@example.com | Standard | 2024-03-20 |
| 3 | Claire Lemaire | claire.lemaire@example.com | Premium | 2022-11-05 |

```python
def query_db(sql: str) -> list[dict]:
    # Accepte uniquement les SELECT (sécurité)
    # Initialise la DB automatiquement si elle n'existe pas
    # Retourne les lignes sous forme de liste de dicts
```

> Note sécurité : `query_db` est réservé aux tests. En production, il faudrait utiliser des requêtes paramétrées et valider les entrées avant d'exécuter du SQL.

---

## Étape 2 — Boucle ReAct (`main.py`)

Le pattern ReAct se déroule en 3 étapes pour chaque requête :

```
Requête utilisateur
      │
      ▼
[REASON] choisir_outil()
  └─ LLM décide : intent + outil + paramètres (JSON)
  └─ Log : intent détecté, outil choisi, raisonnement
      │
      ▼
[ACT] executer_outil()
  ├─ query_db(sql)      → si intent = database
  ├─ search_web(query)  → si intent = search
  └─ (rien)             → si intent = general
  └─ Log : résultat de l'outil
      │
      ▼
[OBSERVE] formuler_reponse()
  └─ LLM synthétise la réponse finale en langage naturel
  └─ Log : réponse finale générée
```

**Schéma JSON de décision utilisé :**

```json
{
  "intent": "database | search | general",
  "outil": "query_db | search_web | reponse_directe",
  "sql": "SELECT * FROM clients WHERE type = 'Premium'",
  "query_recherche": "",
  "raisonnement": "L'utilisateur demande des données clients, j'utilise query_db."
}
```

---

## Étape 3 — Tests

| Test | Intent attendu | Outil attendu | Résultat OK ? |
|---|---|---|---|
| `"Tous les clients Premium"` | `database` | `query_db` | ✓ — Retourne Alice Martin et Claire Lemaire (type=Premium). Réponse finale liste les 2 clients avec leur email et date d'inscription. |
| `"Bonjour"` | `general` | `reponse_directe` | ✓ — Aucun outil exécuté. Le LLM répond directement avec une salutation. Log confirme : *"réponse directe, pas d'exécution d'outil"*. |
| `"Tendances IA 2026"` | `search` | `search_web` | ✓ — Retourne 2 articles simulés sur les LLMs et l'IA enterprise. Réponse finale résume les tendances identifiées. |

### Exemple de logs produits (requête "Tous les clients Premium")

```
2026-04-10 10:00:01 [INFO] __main__ — [ReAct] Intent détecté    : database
2026-04-10 10:00:01 [INFO] __main__ — [ReAct] Outil choisi      : query_db
2026-04-10 10:00:01 [INFO] __main__ — [ReAct] Raisonnement      : L'utilisateur demande des clients de type Premium, j'interroge la base de données.
2026-04-10 10:00:01 [INFO] tools.database — [query_db] Exécution : SELECT * FROM clients WHERE type = 'Premium'
2026-04-10 10:00:01 [INFO] tools.database — [query_db] 2 ligne(s) retournée(s).
2026-04-10 10:00:01 [INFO] __main__ — [ReAct] Résultat query_db : 2 ligne(s)
2026-04-10 10:00:02 [INFO] __main__ — [ReAct] Réponse finale générée.
```

---

## Livrable

- `tools/search.py` : `search_web()` avec banque de résultats simulés par thème
- `tools/database.py` : `query_db()` + `_init_db()` sur SQLite avec 3 clients fictifs
- `main.py` : boucle ReAct complète (`choisir_outil` → `executer_outil` → `formuler_reponse`) avec logging à chaque étape
