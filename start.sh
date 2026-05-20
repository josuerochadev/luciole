#!/bin/sh
# Script de démarrage pour Railway.
# 1. Enrichit les articles pré-collectés au build (LLM, en arrière-plan)
# 2. Démarre l'API immédiatement

echo "[start] Enrichissement des articles en arrière-plan..."
PYTHONUNBUFFERED=1 python startup.py 2>&1 &

echo "[start] Démarrage de l'API..."
# --workers 1 obligatoire : le monitoring in-process n'est pas partagé entre workers.
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
