# ADR-003 — Migration Render vers Railway

**Date** : 2026-05-18
**Statut** : Accepté

---

## Contexte

Le backend était déployé sur **Render** (plan free, région Frankfurt). Plusieurs
contraintes sont apparues en production :

- **Cold start** : le plan free met l'instance en veille après 15 min d'inactivité,
  entraînant des temps de démarrage de 30-60s pour les utilisateurs
- **Éphémère** : pas de volume persistant sur le plan free (tous les fichiers `data/`
  sont réinitialisés à chaque redéploiement)
- **Reverse proxy** : les headers `X-Forwarded-Host` nécessitaient un workaround
  spécifique à Render dans `api.py`

## Décision

Migration vers **Railway** avec la configuration `railway.toml` (builder Nixpacks).

Le fichier `render.yaml` est conservé dans le repo à titre de référence historique
mais n'est plus utilisé pour les déploiements actifs.

**Fichiers affectés :**
- `railway.toml` — nouvelle config de déploiement
- `start.sh` — inchangé (utilise `${PORT:-8000}` compatible Railway)
- `Dockerfile` — mis à jour (`GEMINI_API_KEY`, `DATABASE_URL`)
- `render.yaml` — marqué legacy

## Conséquences

**Positives :**
- Pas de cold start sur le plan Hobby Railway
- Variables d'environnement gérées via le dashboard Railway
- Intégration GitHub pour les déploiements automatiques sur push `main`

**Négatives :**
- `render.yaml` devient un artefact mort (à supprimer une fois la migration stabilisée)
- Le plan Railway est payant au-delà du crédit initial ($5/mois)
