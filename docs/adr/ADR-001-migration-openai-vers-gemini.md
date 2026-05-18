# ADR-001 — Migration OpenAI vers Google Gemini

**Date** : 2026-05-18
**Statut** : Accepté

---

## Contexte

Le projet utilisait l'API OpenAI (gpt-4o-mini, gpt-4o, text-embedding-3-small, Whisper)
pour toutes les opérations LLM. Le quota gratuit OpenAI était limité et la facturation
à l'usage rendait les coûts imprévisibles pour un projet de formation déployé en continu.

## Décision

Migration vers l'API Google Gemini :

| Fonction | Avant | Après |
|---|---|---|
| LLM rapide | gpt-4o-mini | gemini-2.5-flash |
| LLM puissant | gpt-4o | gemini-2.5-pro |
| Embeddings | text-embedding-3-small (1536d) | gemini-embedding-001 |
| Vision | GPT-4o Vision | Gemini Vision |
| Audio | Whisper API | désactivé |

L'API Gemini expose une interface compatible OpenAI (`openai` SDK pointant sur
`https://generativelanguage.googleapis.com/v1beta/openai/`), ce qui a permis une
migration sans réécriture du client (`llm.py`).

## Conséquences

**Positives :**
- Quota gratuit plus généreux (Gemini Flash)
- Variable d'environnement unique : `GEMINI_API_KEY`
- Aucune réécriture du client LLM grâce à la compatibilité API

**Négatives :**
- Transcription audio supprimée (pas d'équivalent Whisper simple dans Gemini)
- Dimension des vecteurs d'embedding différente (ne pas mélanger anciens et nouveaux embeddings)
- Le rapport LLM-as-Judge (`tests/rapport.md`) est obsolète (généré avec gpt-4o)
