"""
Enrichissement d'articles via LLM — partagé entre pipeline.py et startup.py.
"""
import logging

from config import PERTINENCE_MIN
from llm import resumer_article

logger = logging.getLogger(__name__)


def enrichir_article(article: dict) -> dict | None:
    """
    Enrichit un article via le LLM (résumé, catégorie, pertinence, action).
    Retourne l'article enrichi, ou None si la pertinence est en dessous du seuil.

    Args:
        article: Dict avec au moins les clés "titre" et "contenu_complet" ou "resume_brut".

    Returns:
        Le dict article enrichi, ou None si pertinence < PERTINENCE_MIN.
    """
    titre = article.get("titre", "")
    contenu = article.get("contenu_complet", article.get("resume_brut", ""))
    try:
        analyse = resumer_article(titre, contenu)
        pertinence = int(analyse.get("pertinence", 0))
        if pertinence < PERTINENCE_MIN:
            return None
        article.update({
            "resume": analyse.get("resume", contenu[:300]),
            "categorie": analyse.get("categorie", "Autre"),
            "pertinence": pertinence,
            "action": analyse.get("action", "lire"),
        })
        return article
    except Exception as e:
        logger.warning(f"Enrichissement échoué pour '{titre}' : {e}")
        article.setdefault("categorie", "Autre")
        article.setdefault("pertinence", 5)
        return article
