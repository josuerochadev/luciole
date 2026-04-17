"""
Observabilité LLM avec Langfuse.

Initialise le client Langfuse et expose le décorateur @observe()
pour tracer les phases de l'agent ReAct.

Activation : définir LANGFUSE_SECRET_KEY + LANGFUSE_PUBLIC_KEY dans .env
Si les clés sont absentes, tout est no-op (aucun impact sur le fonctionnement).
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Langfuse est optionnel — si non installé ou non configuré, on fournit des no-ops
_langfuse_enabled = False
langfuse = None

try:
    from langfuse import Langfuse, observe as _observe, get_client

    _has_keys = bool(
        os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")
    )

    if _has_keys:
        _langfuse_enabled = True
        langfuse = Langfuse()
        logger.info("[Langfuse] Traçage activé.")
    else:
        logger.info("[Langfuse] Clés absentes — traçage désactivé.")

except ImportError:
    logger.info("[Langfuse] Module non installé — traçage désactivé.")


def observe(*args, **kwargs):
    """Décorateur @observe() : trace la fonction si Langfuse est actif, sinon no-op."""
    if _langfuse_enabled:
        return _observe(*args, **kwargs)

    # No-op : retourne la fonction telle quelle
    def passthrough(fn):
        return fn
    if args and callable(args[0]):
        return args[0]
    return passthrough


def flush():
    """Flush les traces en attente (à appeler en fin de requête si besoin)."""
    if _langfuse_enabled and langfuse is not None:
        langfuse.flush()


def update_current_trace(**kwargs):
    """Met à jour la trace courante (tags, metadata, user_id, etc.)."""
    if not _langfuse_enabled:
        return
    try:
        client = get_client()
        if client is not None:
            client.update_current_trace(**kwargs)
    except Exception:
        pass


def score_current_trace(name: str, value: float, comment: str = None):
    """Ajoute un score à la trace courante (ex: qualité de réponse)."""
    if not _langfuse_enabled:
        return
    try:
        client = get_client()
        if client is not None:
            client.score_current_trace(name=name, value=value, comment=comment)
    except Exception:
        pass
