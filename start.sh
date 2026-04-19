#!/bin/sh
# Script de démarrage pour Render (et autres hébergeurs).
# 1. Lance le pipeline RSS en arrière-plan (sans bloquer)
# 2. Démarre l'API immédiatement

echo "[start] Lancement du pipeline RSS en arrière-plan..."
python pipeline.py --no-email &

echo "[start] Démarrage de l'API..."
exec uvicorn api:app --host 0.0.0.0 --port 8000
