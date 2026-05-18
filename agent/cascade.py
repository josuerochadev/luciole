"""
Cascade M6E3 — classification de la complexité des requêtes.
Choisit le modèle LLM (rapide vs. puissant) selon la complexité détectée.
"""
import logging

from config import MODEL_FAST, MODEL_POWERFUL
from llm import appeler_llm_json
from tracing import observe
from agent.prompts import PROMPT_COMPLEXITE

logger = logging.getLogger(__name__)


@observe(name="classifier_complexite")
def classifier_complexite(requete: str) -> dict:
    """
    Classifie la complexité d'une requête avec le modèle rapide.

    Returns:
        {"complexite": "simple"|"complexe", "categorie": "..."}.
        Fallback vers "complexe" si le parsing échoue.
    """
    try:
        result = appeler_llm_json(
            PROMPT_COMPLEXITE.format(question=requete),
            schema={"complexite": "simple|complexe", "categorie": "salutation|faq|raisonnement|code|analyse"},
            system_prompt="Tu es un classificateur de requêtes. Réponds uniquement en JSON.",
        )
        if result.get("complexite") not in ("simple", "complexe"):
            result["complexite"] = "complexe"
        if "categorie" not in result:
            result["categorie"] = "raisonnement"
        return result
    except Exception as e:
        logger.warning(f"[Cascade] Classification échouée, fallback complexe : {e}")
        return {"complexite": "complexe", "categorie": "raisonnement"}


def choisir_modele(complexite: str) -> str:
    """Retourne le modèle à utiliser selon la complexité."""
    return MODEL_FAST if complexite == "simple" else MODEL_POWERFUL
