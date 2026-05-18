"""
Étapes 1 et 2 du cycle ReAct :
  1. Raisonnement — choisir_outil() : sélection via function calling
  2. Action       — executer_outil() : exécution et retour du résultat brut
"""
import json
import logging
import os

from llm import appeler_llm_tools
from security import valider_sql
from tools.database import query_db
from tools.email import envoyer_rapport, selectionner_articles
from tools.rag import rechercher_articles
from tools.search import search_web
from tools.vision import analyser_image
from tracing import observe
from agent.prompts import SYSTEM_REACT, TOOLS_DECISION

logger = logging.getLogger(__name__)


@observe(name="choisir_outil")
def choisir_outil(requete: str, historique: list[dict] | None = None, model: str | None = None) -> dict:
    """Demande au LLM quel outil utiliser via function calling natif."""
    messages = [{"role": "system", "content": SYSTEM_REACT}]
    if historique:
        messages.extend(historique)
    messages.append({"role": "user", "content": f"Requête de l'utilisateur : {requete}"})
    decision = appeler_llm_tools(messages=messages, tools=TOOLS_DECISION, model=model)
    logger.info(f"[ReAct] Intent détecté    : {decision.get('intent', '?')}")
    logger.info(f"[ReAct] Outil choisi      : {decision.get('outil', '?')}")
    logger.info(f"[ReAct] Raisonnement      : {decision.get('raisonnement', '?')}")
    return decision


@observe(name="executer_outil")
def executer_outil(decision: dict) -> str:
    """Exécute l'outil indiqué dans la décision et retourne le résultat en texte."""
    outil = decision.get("outil", "reponse_directe")

    if outil == "query_db":
        sql = decision.get("sql", "SELECT * FROM clients")
        sql_ok, sql_msg = valider_sql(sql)
        if not sql_ok:
            logger.warning(f"[ReAct] SQL bloqué par security : {sql}")
            return f"[ERREUR_SECURITE] {sql_msg}"
        try:
            lignes = query_db(sql)
            if not lignes:
                logger.info("[ReAct] query_db : 0 ligne retournée.")
                return "[AUCUN_RESULTAT] La requête n'a retourné aucune donnée."
            logger.info(f"[ReAct] Résultat query_db : {len(lignes)} ligne(s)")
            return json.dumps(lignes, ensure_ascii=False, indent=2)
        except (ValueError, RuntimeError) as e:
            resultat = f"[ERREUR_OUTIL] La requête SQL a échoué : {e}"
            logger.error(f"[ReAct] {resultat}")
            return resultat

    elif outil == "search_web":
        query = decision.get("query_recherche", "")
        resultats = search_web(query)
        if not resultats:
            return "[AUCUN_RESULTAT] La recherche web est indisponible (clé API Tavily non configurée) ou n'a retourné aucun résultat."
        logger.info(f"[ReAct] Résultat search_web : {len(resultats)} résultat(s)")
        return json.dumps(resultats, ensure_ascii=False, indent=2)

    elif outil == "search_articles":
        query = decision.get("query_recherche", "")
        try:
            resultats = rechercher_articles(query, n=5)
            if not resultats:
                return "[AUCUN_RESULTAT] Aucun article archivé ne correspond à cette requête."
            logger.info(f"[ReAct] Résultat search_articles (RAG) : {len(resultats)} résultat(s)")
            return json.dumps(resultats, ensure_ascii=False, indent=2)
        except Exception as e:
            resultat = f"[ERREUR_OUTIL] Recherche sémantique échouée : {e}"
            logger.error(f"[ReAct] {resultat}")
            return resultat

    elif outil == "analyze_image":
        fichier = decision.get("file_path", "")
        # Reconstituer le chemin absolu si le LLM n'a reçu que le nom de fichier
        if fichier and not os.path.isabs(fichier):
            from config import UPLOAD_DIR
            fichier = os.path.join(UPLOAD_DIR, fichier)
        consigne = decision.get("query_recherche", None) or None
        try:
            result = analyser_image(fichier, consigne=consigne)
            logger.info(f"[ReAct] Résultat analyze_image : {len(result)} clé(s) extraites")
            return json.dumps(result, ensure_ascii=False, indent=2)
        except (FileNotFoundError, ValueError) as e:
            resultat = f"[ERREUR_OUTIL] Analyse image impossible : {e}"
            logger.error(f"[ReAct] {resultat}")
            return resultat
        except RuntimeError as e:
            resultat = f"[ERREUR_OUTIL] Erreur Gemini Vision : {e}"
            logger.error(f"[ReAct] {resultat}")
            return resultat

    elif outil == "preview_digest":
        try:
            articles = selectionner_articles(nb_max=20)
            if not articles:
                return "[AUCUN_RESULTAT] Aucun article pertinent disponible pour le digest."
            categories: dict[str, list[str]] = {}
            for a in articles:
                cat = a.get("categorie", "Autre")
                categories.setdefault(cat, []).append(a.get("titre", "Sans titre"))
            resume = {
                "nb_articles": len(articles),
                "categories": {cat: len(arts) for cat, arts in categories.items()},
                "top_articles": [
                    {"titre": a.get("titre", ""), "categorie": a.get("categorie", ""),
                     "pertinence": a.get("pertinence", 0)}
                    for a in articles[:5]
                ],
            }
            logger.info(f"[ReAct] Résultat preview_digest : {len(articles)} article(s)")
            return json.dumps(resume, ensure_ascii=False, indent=2)
        except Exception as e:
            resultat = f"[ERREUR_OUTIL] Prévisualisation du digest échouée : {e}"
            logger.error(f"[ReAct] {resultat}")
            return resultat

    elif outil == "send_digest":
        try:
            result = envoyer_rapport(dry_run=False)
            logger.info(f"[ReAct] Résultat send_digest : {result.get('message', '?')}")
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            resultat = f"[ERREUR_OUTIL] Envoi du digest échoué : {e}"
            logger.error(f"[ReAct] {resultat}")
            return resultat

    else:  # reponse_directe
        logger.info("[ReAct] Outil : réponse directe, pas d'exécution d'outil.")
        return (
            "(aucun outil — réponse directe du LLM)\n"
            "Rappel : tu es Luciole, agent de veille technologique. "
            "Si la requête est hors périmètre tech, recadre poliment."
        )
