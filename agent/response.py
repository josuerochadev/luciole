"""
Étape 3 du cycle ReAct : formulation de la réponse finale à partir
du résultat brut de l'outil.
"""
import logging

from llm import appeler_llm
from tracing import observe
from agent.prompts import _FORMAT_DIRECT, _FORMATS_PAR_INTENT, _REGLES_FIDELITE

logger = logging.getLogger(__name__)


def _construire_prompt_reponse(requete: str, resultat_outil: str, intent: str) -> str:
    """Construit le prompt final pour la réponse LLM à partir du résultat de l'outil.
    Partagé entre formuler_reponse() (synchrone) et agent_react_stream() (streaming)."""
    if resultat_outil.startswith("[ERREUR_OUTIL]"):
        instruction = (
            "L'outil a retourné une erreur. "
            "Informe l'utilisateur que la donnée est inaccessible. "
            "N'invente AUCUN chiffre, nom ou donnée — dis clairement que tu ne sais pas."
        )
    elif resultat_outil.startswith("[AUCUN_RESULTAT]"):
        instruction = (
            "L'outil n'a trouvé aucune donnée correspondante. "
            "Informe l'utilisateur qu'aucun résultat n'existe pour sa requête. "
            "NE JAMAIS inventer de titre d'article, d'URL, de chiffre ou de date pour combler ce vide."
        )
    else:
        format_instruction = _FORMATS_PAR_INTENT.get(intent, _FORMAT_DIRECT)
        instruction = (
            "Formule une réponse claire et structurée en français pour l'utilisateur.\n\n"
            f"{format_instruction}\n"
            f"{_REGLES_FIDELITE}"
        )
    return (
        f"Requête initiale : {requete}\n\n"
        f"Résultat de l'outil :\n{resultat_outil}\n\n"
        f"{instruction}"
    )


@observe(name="formuler_reponse")
def formuler_reponse(
    requete: str,
    resultat_outil: str,
    intent: str = "general",
    historique: list[dict] | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Demande au LLM de formuler une réponse finale à partir du résultat de l'outil."""
    prompt = _construire_prompt_reponse(requete, resultat_outil, intent)
    return appeler_llm(prompt, historique=historique, model=model, max_tokens=max_tokens)
