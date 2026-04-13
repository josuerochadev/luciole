"""
Gestion de la mémoire conversationnelle de l'agent (exercice 4).
Stocke les messages en mémoire avec une limite de 10 entrées.
"""
import logging
from collections import deque

logger = logging.getLogger(__name__)

LIMITE_MEMOIRE = 10

# Mémoire de session : deque avec taille maximale fixe
_memoire: deque[dict] = deque(maxlen=LIMITE_MEMOIRE)


def store(message: str, role: str = "user") -> None:
    """
    Ajoute un message en mémoire.
    Si la mémoire est pleine (10 messages), le plus ancien est automatiquement
    supprimé (comportement du deque avec maxlen).

    Args:
        message: Le contenu du message.
        role:    "user" ou "assistant".
    """
    entree = {"role": role, "content": message}
    _memoire.append(entree)
    logger.debug(f"[memory] store() — {len(_memoire)}/{LIMITE_MEMOIRE} messages. Role={role}")


def recall(n: int = 5) -> list[dict]:
    """
    Retourne les n derniers messages de la mémoire (du plus ancien au plus récent).

    Args:
        n: Nombre de messages à rappeler (défaut : 5).

    Returns:
        Liste de dicts {role, content}.
    """
    messages = list(_memoire)
    résultat = messages[-n:] if n < len(messages) else messages
    logger.debug(f"[memory] recall({n}) — {len(résultat)} message(s) retourné(s).")
    return résultat


def clear() -> None:
    """Vide complètement la mémoire de session."""
    _memoire.clear()
    logger.debug("[memory] clear() — mémoire vidée.")


def taille() -> int:
    """Retourne le nombre de messages actuellement en mémoire."""
    return len(_memoire)


# ---------------------------------------------------------------------------
# Contexte mémoire pour l'agent ReAct
# ---------------------------------------------------------------------------

class ContexteAgent:
    """
    Contexte de la session courante de l'agent de veille.
    Conserve les articles collectés, filtrés, résumés et prêts à l'envoi.
    """

    def __init__(self):
        self.articles_bruts: list[dict] = []
        self.articles_filtres: list[dict] = []
        self.articles_enrichis: list[dict] = []
        self.articles_rapport: list[dict] = []

    def charger_articles_existants(self) -> list[dict]:
        from tools.database import charger_json
        from config import ARTICLES_FILE
        return charger_json(ARTICLES_FILE)

    def ajouter_articles_bruts(self, articles: list[dict]) -> None:
        liens_connus = {a["lien"] for a in self.articles_bruts}
        nouveaux = [a for a in articles if a["lien"] not in liens_connus]
        self.articles_bruts.extend(nouveaux)
        logger.info(f"Contexte : {len(nouveaux)} articles bruts ajoutés ({len(self.articles_bruts)} total).")

    def filtrer_nouveaux(self) -> list[dict]:
        from tools.database import article_deja_traite
        nouveaux = [a for a in self.articles_filtres if not article_deja_traite(a["lien"])]
        logger.info(f"Articles nouveaux (non traités) : {len(nouveaux)}/{len(self.articles_filtres)}")
        return nouveaux

    def ajouter_article_enrichi(self, article: dict) -> None:
        self.articles_enrichis.append(article)

    def grouper_par_categorie(self) -> dict[str, list[dict]]:
        groupes: dict[str, list[dict]] = {}
        for article in self.articles_rapport:
            cat = article.get("categorie", "Autre")
            groupes.setdefault(cat, []).append(article)
        return groupes

    def selectionner_pour_rapport(self, pertinence_min: int = 5, max_articles: int = 20) -> None:
        pertinents = [a for a in self.articles_enrichis if a.get("pertinence", 0) >= pertinence_min]
        pertinents.sort(key=lambda a: a.get("pertinence", 0), reverse=True)
        self.articles_rapport = pertinents[:max_articles]
        logger.info(f"Rapport : {len(self.articles_rapport)} articles sélectionnés.")

    def resume_session(self) -> str:
        return (
            f"Session courante :\n"
            f"  - Bruts récupérés : {len(self.articles_bruts)}\n"
            f"  - Après filtrage thématique : {len(self.articles_filtres)}\n"
            f"  - Résumés par LLM : {len(self.articles_enrichis)}\n"
            f"  - Dans le rapport final : {len(self.articles_rapport)}"
        )
