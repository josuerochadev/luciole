# Exercice 2 — Appeler le LLM et structurer la réponse en JSON

*Alex Dubus - Zhengfeng Ding - Josue Xavier Rocha - Stéphanie Consoli*

---

## Étape 1 — Fonction `appeler_llm_json()`

Ajoutée dans `llm.py`. La fonction reçoit une liste d'objets `Article`, construit un prompt de synthèse, et demande au LLM de répondre **uniquement en JSON valide** selon le schéma de synthèse du rapport quotidien.

Le parsing de la réponse est délégué à `_extraire_json()` :

```python
def _extraire_json(texte: str) -> dict:
    """
    Parse la réponse du LLM en JSON.
    Fallback regex si le LLM entoure le JSON de texte parasite (ex: ```json ... ```).
    """
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", texte, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Aucun JSON valide trouvé dans la réponse du LLM :\n{texte}")
```

```python
def appeler_llm_json(articles: list[Article], modele: str = "gpt-4o-mini") -> dict:
    """
    Envoie les articles à ChatGPT et retourne la synthèse sous forme de dict JSON.

    Structure retournée :
    {
        "titre": str,
        "themes": [{"nom": str, "resume": str, "points_cles": [str]}],
        "conclusion": str
    }

    Args:
        articles: Liste des articles à synthétiser.
        modele:   Modèle OpenAI à utiliser.

    Returns:
        Dict Python issu du JSON retourné par le LLM.
    """
    if not articles:
        return {"titre": "Aucun article", "themes": [], "conclusion": "Aucun article à synthétiser."}

    contenu_articles = _construire_prompt(articles)

    system_prompt = (
        "Tu es un expert en veille technologique. "
        "Tu reçois une liste d'articles récents dans le domaine de l'informatique. "
        "Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, respectant ce schéma :\n"
        "{\n"
        '  "titre": "Synthèse de veille technologique du <date>",\n'
        '  "themes": [\n'
        '    {"nom": "<thème>", "resume": "<résumé du thème>", "points_cles": ["<point>", ...]}\n'
        "  ],\n"
        '  "conclusion": "<tendances générales et points à retenir>"\n'
        "}\n"
        "Regroupe les articles par thème. Sois concis et professionnel."
    )

    user_prompt = (
        f"Voici {len(articles)} article(s) de veille technologique :\n\n"
        f"{contenu_articles}\n"
        "Produis la synthèse JSON."
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=modele,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    brut = response.choices[0].message.content.strip()
    return _extraire_json(brut)
```

---

## Étape 2 — Schéma JSON adapté au projet de veille technologique

`appeler_llm_json()` produit une **synthèse groupée** de plusieurs articles. Le schéma de sortie est :

```json
{
  "titre": "Synthèse de veille technologique du 10/04/2026",
  "themes": [
    {
      "nom": "Intelligence Artificielle",
      "resume": "Résumé du thème en 2-3 phrases.",
      "points_cles": ["Point 1", "Point 2", "Point 3"]
    }
  ],
  "conclusion": "Tendances générales et points à retenir."
}
```

Pour l'analyse individuelle d'un article (fonction `resumer_article()`), un second schéma est utilisé :

```json
{
  "pertinence": 9,
  "categorie": "IA | Cybersécurité | Cloud | Infrastructure | DevOps | Données | Hors-sujet | Autre",
  "resume": "résumé factuel en 2-3 phrases maximum",
  "action": "lire | archiver | ignorer"
}
```

**Exemple avec un message réaliste** (article sur les GPU NVIDIA) :

```json
{
  "pertinence": 9,
  "categorie": "IA",
  "resume": "NVIDIA annonce une nouvelle architecture de puces graphiques optimisée pour les LLMs. Les performances en inférence sont multipliées par 4 par rapport à la génération précédente. Cette technologie cible directement les datacenters des hyperscalers.",
  "action": "lire"
}
```

---

## Étape 3 — Tests des cas limites

> **Lecture du tableau** : la colonne *Réponse brute LLM* montre ce que le modèle retourne **sans contrainte JSON** (comportement naturel). La colonne *Résultat avec `appeler_llm_json()`* montre ce que la fonction retourne après application du prompt structuré et du parsing.

| Test | Prompt | Réponse brute LLM (sans contrainte JSON) | Résultat avec `appeler_llm_json()` |
|---|---|---|---|
| **Message ambigu** | `"Salut, ça va ?"` | *"Salut ! Oui, ça va bien, et toi ?"* | JSON valide sans fallback. `pertinence: 1`, `categorie: "Hors-sujet"`, `action: "ignorer"`. Le résumé indique sobrement que le message est une salutation sans lien avec la veille technologique. |
| **Message long** | Email de 500 mots (migration AWS) | *"Bien sûr ! Tu veux un email de 500 mots sur quel sujet, pour qui, et avec quel ton ?"* | JSON valide retourné directement. `pertinence: 8`, `categorie: "Cloud"`, `action: "lire"`. Le résumé condense les points clés (architecture multi-comptes, AWS DMS, budget 85k€) en 2-3 phrases. |
| **Hors sujet** | `"Quelle est la capitale de la France ?"` | *"La capitale de la France est Paris."* | JSON valide. `pertinence: 1`, `categorie: "Hors-sujet"`, `action: "ignorer"`. Le LLM ne force pas de lien artificiel avec la tech — comportement attendu. |
| **Message agressif** | `"Votre service est NUL"` | *"Je suis désolé que vous soyez frustré. Dites-moi ce qui ne va pas..."* | JSON valide. `pertinence: 1`, `categorie: "Autre"`, `action: "ignorer"`. Le LLM reste factuel et neutre, sans reproduire ni amplifier l'agressivité. |

---

## Livrable

- `llm.py` : fonctions `appeler_llm_json()` et `_extraire_json()` opérationnelles
- `test_llm_json.py` : 4 tests documentés avec assertions sur la structure du JSON retourné
- `resumer_article()` utilise un schéma dédié à l'analyse individuelle d'article
