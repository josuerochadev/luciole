# Luciole — TODO (21 mai 2026)

## Etat des lieux (20 mai)

- 1852 articles en base (Neon PostgreSQL), tous "Non classe"
- 0 articles enrichis (quota Gemini epuise)
- 1605 articles avec contenu scrape (87%)
- 1341 avec resume brut RSS, 511 sans aucun resume
- Cache JSON local : `data/articles_scraped.json` (1853 articles)
- Scripts `pipeline_no_llm.py` et `enrichir_articles.py` prets
- Refonte UI articles/digest commitee (grille magazine 2 colonnes)
- 5 commits en avance sur origin (pas encore pushes)

## Priorite 1 — Enrichir les articles via Gemini

Le quota Gemini se reset. Lancer l'enrichissement retroactif :

```bash
# 1. Tester d'abord en dry-run
python enrichir_articles.py --limit 100 --dry-run

# 2. Lancer par batches progressifs
python enrichir_articles.py --limit 500

# 3. Si le quota tient, continuer
python enrichir_articles.py
```

- Batch commit tous les 50 articles (resilient aux crashes)
- Si le quota coupe : relancer plus tard, le script ne re-traite que les "Non classe"
- 5 workers LLM en parallele (ajustable dans `enrichir_articles.py`)

## Priorite 2 — Valider le rendu UI avec des vraies donnees

Une fois des articles enrichis (categories + pertinence) :

- [ ] Page **Articles** : filtrage par categorie, tri par pertinence, pagination
- [ ] Page **Digest** : presentation des articles les mieux notes
- [ ] Fallback `resume_brut` quand `resume` est vide
- [ ] Categories avec les bonnes couleurs (IA, Cloud, Cyber, DevOps, Data, Infra)
- [ ] Layout 2 colonnes equilibre
- [ ] Responsive mobile

## Priorite 3 — Corrections UI

Ajustements identifies apres test avec donnees reelles :

- [ ] Mapper les categories Gemini aux classes CSS (`cat-ia`, `cat-cloud`, etc.)
- [ ] Verifier que le score de pertinence s'affiche correctement
- [ ] Tester les etats vides (aucun article dans une categorie)
- [ ] Verifier la pagination avec 1800+ articles

## Priorite 4 — Push et deploy

- [ ] Pousser les 5+ commits sur origin
- [ ] Verifier le deploiement Railway
- [ ] Tester en production

## Backlog (de MEMORY.md)

- [ ] Mettre a jour docs/ARCHITECTURE.md
- [ ] Ajouter LICENSE a la racine
- [ ] Verifier slug LinkedIn dans footer README
- [ ] Ajouter URL de demo + screenshot dans README
- [ ] Reecrire TestArticles avec mock PostgreSQL
- [ ] Nettoyer references OpenAI dans test_qualite.py / test_streaming.py
