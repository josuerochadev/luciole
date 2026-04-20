#!/bin/sh
# Script de démarrage pour Render (et autres hébergeurs).
# 1. Enrichit les articles pré-collectés au build (LLM, en arrière-plan)
# 2. Démarre l'API immédiatement

echo "[start] Enrichissement des articles en arrière-plan..."
PYTHONUNBUFFERED=1 python startup.py 2>&1 &

echo "[start] Démarrage de l'API..."
exec uvicorn api:app --host 0.0.0.0 --port 8000
