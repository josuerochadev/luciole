# Luciole — TODO (21 mai 2026)

## Fait

- [x] **P1 — Enrichissement Gemini** : 1813/1852 articles enrichis (97%), 0 erreurs
- [x] Fix bug RealDictCursor dans `enrichir_articles.py`
- [x] **P2 — Rendu UI** : filtrage categorie, tri pertinence, pagination, fallback resume_brut
- [x] **P3 — Corrections UI** : mapping categories CSS, scores, spacings harmonises, traits fins
- [x] Digest limite a 20 articles (au lieu de 100), KPIs redondants supprimes
- [x] Push origin (tous commits pushes)

## En cours — Deploy

- [ ] Verifier le deploiement Railway
- [ ] Tester en production

## Backlog

- [ ] Mettre a jour docs/ARCHITECTURE.md
- [ ] Ajouter LICENSE a la racine
- [ ] Verifier slug LinkedIn dans footer README
- [ ] Ajouter URL de demo + screenshot dans README
- [ ] Reecrire TestArticles avec mock PostgreSQL
- [ ] Nettoyer references OpenAI dans test_qualite.py / test_streaming.py
