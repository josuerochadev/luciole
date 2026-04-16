# UI Streamlit — Agent de veille technologique

Interface utilisateur pour le fil rouge. Consomme l'API FastAPI (`fil-rouge/api.py`).

## Architecture

```
 [Navigateur]
      │
      ▼
 [Streamlit UI]  ── HTTP ──▶  [FastAPI /ask, /metrics]  ──▶  [Agent ReAct]
 (port 8501)                  (port 8000)
```

## Fonctionnalités

### Page Chat
- Conversation multitour (historique dans `st.session_state`)
- Input texte (`st.chat_input`)
- Upload optionnel d'un fichier audio (transcribe) ou image (vision)
- Affichage de la latence par réponse
- Export de la conversation en markdown

### Page Dashboard
- KPIs : nb requêtes, latence moy./p95, tokens, coût
- Santé : taux d'erreur et de fallback
- Graphe de latence des 50 dernières requêtes
- Tableau détaillé des requêtes récentes
- Auto-refresh optionnel (10s)

## Installation

```bash
# Depuis fil-rouge/, dans le venv du projet
pip install -r ui/requirements.txt
```

## Lancement

Deux terminaux :

```bash
# Terminal 1 — API
cd fil-rouge
uvicorn api:app --reload

# Terminal 2 — UI
cd fil-rouge
streamlit run ui/streamlit_app.py
```

L'UI ouvre automatiquement le navigateur sur http://localhost:8501.

## Configuration

Variable d'environnement optionnelle :

| Variable | Défaut | Description |
|---|---|---|
| `AGENT_API_URL` | `http://localhost:8000` | URL du backend FastAPI |

Exemple pour pointer sur un backend dockerisé :

```bash
AGENT_API_URL=http://localhost:9000 streamlit run ui/streamlit_app.py
```

## Upload de fichiers

Les fichiers audio/image uploadés sont sauvegardés dans `fil-rouge/data/uploads/`
avec un préfixe UUID pour éviter les collisions. Le chemin relatif est ensuite
injecté dans la question envoyée à l'agent, qui route vers `transcribe_audio`
ou `analyze_image` selon le type.
