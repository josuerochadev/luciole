# Exercice 4 — Ajouter la mémoire à l'agent

*Alex Dubus - Zhengfeng Ding - Josue Xavier Rocha - Stéphanie Consoli*

---

## Étape 1 — `memory/store.py`

La mémoire est implémentée avec un `deque(maxlen=10)` : structure Python qui écrase automatiquement les messages les plus anciens quand la limite est atteinte.

**3 fonctions exposées :**

```python
def store(message: str, role: str = "user") -> None:
    """Ajoute un message {role, content} en mémoire. Écrase le plus ancien si pleine."""

def recall(n: int = 5) -> list[dict]:
    """Retourne les n derniers messages, du plus ancien au plus récent."""

def clear() -> None:
    """Vide complètement la mémoire de session."""
```

**Injection du contexte dans le LLM :**

```python
def repondre_avec_memoire(question: str) -> str:
    historique = recall(n=10)
    messages_contexte = "\n".join(f"{m['role'].upper()} : {m['content']}" for m in historique)
    prompt = f"Historique :\n{messages_contexte}\n\nNouvelle question : {question}"
    reponse = appeler_llm(prompt)
    store(question, role="user")
    store(reponse, role="assistant")
    return reponse
```

---

## Étape 2 — Tests : Sans mémoire vs Avec mémoire

| Test | Sans mémoire | Avec mémoire |
|---|---|---|
| **"Je m'appelle Alice"** puis **"Comment je m'appelle ?"** | *"Je ne dispose pas d'informations sur votre identité. Mon rôle est de fournir des informations et d'analyser des articles."* — Le LLM ne peut pas répondre, les deux appels sont indépendants. | *"Vous vous appelez Alice."* — Le premier message est injecté dans le prompt, la mémoire relie les deux échanges. |
| **3 questions enchaînées sur les LLMs** | Q2 *"Quels sont les plus connus ?"* → *"Pourriez-vous préciser de quoi vous parlez ?"*. Q3 → même confusion. Sans contexte, les questions sont ambiguës et le LLM ne sait pas à quoi elles se réfèrent. | Q2 → liste complète (GPT-3, BERT, LLaMA...). Q3 → *"Le modèle le plus utilisé en entreprise est GPT-3..."*. Chaque réponse s'appuie sur les précédentes. Cohérence conversationnelle maintenue. |
| **12 messages envoyés, rappel du 1er** | Sans mémoire, aucun message n'est conservé. | Seuls les 10 derniers messages sont conservés (`maxlen=10`). Messages 1 et 2 automatiquement écrasés. `recall()` retourne *"Message numéro 3"* comme premier. Assertion `taille() == 10` : ✓ PASS. |

---

## Livrable

- `memory/store.py` : `store()`, `recall()`, `clear()` avec `deque(maxlen=10)`
- `test_memory.py` : 3 tests documentés avec assertions sur la limite de mémoire
- Intégration dans la boucle ReAct via `repondre_avec_memoire()`
