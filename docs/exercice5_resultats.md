# Exercice 5 — Débugger un agent défaillant

*Alex Dubus - Zhengfeng Ding - Josue Xavier Rocha - Stéphanie Consoli*

---

## Étape 1 — Analyse des 3 logs défaillants

### Log A — L'agent qui ignore les outils

```
09:14:02 INFO Requête : "Combien d'articles IA ont été collectés aujourd'hui ?"
09:14:03 INFO Intent : general
09:14:03 INFO Tool : réponse_directe
09:14:04 INFO Réponse : "Consultez votre tableau de bord."
```

| Élément | Réponse |
|---|---|
| **Symptôme** | L'agent classe l'intent en `general` alors que la question porte sur des données internes (articles collectés), et répond de façon vague sans interroger la base locale. |
| **Cause racine** | Le system prompt de détection d'intent ne mentionne pas les articles, comptages ou statistiques de veille comme cas d'usage de `query_db`. Le LLM ne reconnaît pas ce mot-clé métier. |
| **Correction proposée** | Enrichir le system prompt : ajouter explicitement `articles collectés, nombre d'articles, statistiques de veille, comptages, score de pertinence` dans les exemples de `query_db`. ✓ *Implémenté dans `SYSTEM_REACT`.* |

---

### Log B — L'agent qui hallucine des données

```
09:15:01 INFO Requête : "Quel est le score de pertinence de l'article sur NVIDIA ?"
09:15:02 INFO Tool : query_db
09:15:02 ERROR Tool erreur : no such column: pertinence
09:15:03 INFO Réponse : "L'article sur NVIDIA a un score de pertinence de 8/10."
```

| Élément | Réponse |
|---|---|
| **Symptôme** | L'outil échoue avec une erreur SQL (colonne `pertinence` absente de la table interrogée), mais le LLM génère quand même une réponse avec un score inventé (8/10). |
| **Cause racine** | Le message d'erreur de l'outil est passé au LLM sans instruction explicite d'honnêteté. Le LLM, entraîné à être utile, comble le vide avec une hallucination plutôt que d'admettre l'échec. |
| **Correction proposée** | Préfixer les erreurs d'outil avec `[ERREUR_OUTIL]` et injecter dans le prompt de formulation l'instruction : *"N'invente AUCUNE donnée — dis clairement que tu ne sais pas."* ✓ *Implémenté dans `executer_outil()` et `formuler_reponse()`.* |

---

### Log C — L'agent qui tourne en boucle

```
09:16:01 INFO Requête : "Résume les articles sur le quantum computing"
09:16:02 INFO Itération 1 | Tool : search_web → résultats non pertinents
09:16:04 INFO Itération 2 | Tool : search_web → résultats non pertinents
09:16:06 INFO Itération 3 | Tool : search_web → Max itérations. Abandon.
```

| Élément | Réponse |
|---|---|
| **Symptôme** | L'agent répète le même outil (`search_web`) à chaque itération sans changer de stratégie, jusqu'à atteindre la limite. |
| **Cause racine** | Le quantum computing n'est pas dans les thèmes surveillés ni dans la banque de résultats simulés. L'agent n'a pas de mémoire inter-itérations : il choisit `search_web` à chaque fois sans retenir que les résultats précédents étaient non pertinents. |
| **Correction proposée** | Tracker les outils déjà essayés (`outils_essayes`). Si le même outil est choisi une seconde fois, basculer en `reponse_directe` en reconnaissant que ce sujet n'est pas couvert par les sources surveillées. ✓ *Implémenté dans `agent_react()` avec `MAX_ITERATIONS = 2`.* |

---

## Étape 2 — Requêtes pièges sur notre agent

| Requête piège | Comportement attendu | Comportement observé | Diagnostic |
|---|---|---|---|
| `"Tendence sur l IA en 2026"` (faute de frappe) | `search_web` — le LLM doit inférer `tendances IA 2026` malgré les fautes | Intent `search`, `search_web` retourne les articles IA simulés. Réponse cohérente sur les LLMs et l'IA enterprise. | ✓ Robuste aux fautes d'orthographe : les LLMs normalisent naturellement les requêtes avant de choisir l'outil. |
| `"Montre les articles Cloud ET envoie le rapport par email"` (2 intentions) | Choix d'un outil prioritaire (`query_db` ou `search_web`), la partie email non traitée | Intent `search`, traite la partie Cloud. L'envoi email n'est pas déclenché — l'agent ne gère qu'une intention par appel. | Limite identifiée : l'architecture ReAct mono-étape ne supporte pas les requêtes composites. Une séquence planifiée serait nécessaire. |
| `"Quel est le score de pertinence de l'article sur NVIDIA ?"` (données inexistantes) | `query_db` échoue (colonne absente), le LLM reconnaît l'absence sans inventer | `[ERREUR_OUTIL]` détecté — réponse : *"La colonne demandée n'existe pas dans la base. Je ne dispose pas de cette information."* Aucune hallucination. | ✓ Correction Log B efficace — l'instruction anti-hallucination fonctionne. |
| Requête de 300+ mots sur IA/GPU/cybersécurité/Cloud (requête très longue) | `search_web`, réponse synthétique sans timeout ni troncature | Intent `search`, `search_web` retourne les résultats IA. Réponse générée correctement malgré le contexte long. | ✓ GPT-4o-mini gère bien les prompts longs. La troncature à 2000 caractères dans `resumer_article` protège en cas de contenu RSS très volumineux. |

---

## Corrections implémentées (`main.py`)

| Correction | Emplacement | Détail |
|---|---|---|
| **Log A** — Intent trop restrictif | `SYSTEM_REACT` | Ajout de `articles collectés, statistiques de veille, score de pertinence` dans les exemples de `query_db` |
| **Log B** — Hallucination sur erreur outil | `executer_outil()` + `formuler_reponse()` | Préfixe `[ERREUR_OUTIL]` + instruction stricte d'honnêteté au LLM |
| **Log C** — Boucle infinie | `agent_react()` | `MAX_ITERATIONS = 2` + tracking `outils_essayes` — bascule en réponse directe si répétition |

---

## Livrable

- `main.py` : 3 corrections implémentées (intent, anti-hallucination, anti-boucle)
- `test_agent_debug.py` : 4 requêtes pièges documentées et testées
