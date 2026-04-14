"""
Point d'entrée de l'agent de veille technologique.
Exercice 3 : boucle ReAct (Reason + Act).

Utilisation : python main.py
"""
import json
import logging
import sys

from llm import appeler_llm, appeler_llm_json
from tools.search import search_web
from tools.database import query_db
from tools.rag import rechercher_articles
from tools.transcribe import transcrire_audio
from tools.vision import analyser_image
from security import analyser_securite, valider_sql, filtrer_sortie

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schéma de décision ReAct
# ---------------------------------------------------------------------------
SCHEMA_DECISION = {
    "intent": "database | search | rag | transcribe | vision | general",
    "outil": "query_db | search_web | search_articles | transcribe_audio | analyze_image | reponse_directe",
    "sql": "requête SQL si intent=database, sinon chaîne vide",
    "query_recherche": "requête si intent=search ou rag, sinon chaîne vide",
    "file_path": "chemin du fichier si intent=transcribe ou vision, sinon chaîne vide",
    "raisonnement": "explication courte du choix de l'outil",
}

SYSTEM_REACT = (
    "Tu es un agent de veille technologique. "
    "Quand tu reçois une requête, tu dois choisir le bon outil parmi :\n"
    "- query_db : pour toute question sur des clients, données internes, base de données, "
    "tickets, statistiques, chiffres internes, comptages, score de pertinence, KPIs\n"
    "- search_web : pour toute question sur des tendances, actualités, technologies récentes, "
    "nouveautés, veille externe\n"
    "- search_articles : pour toute question sur des articles DÉJÀ collectés et archivés "
    "('quels articles parlent de...', 'résume ce qu'on a sur...', 'retrouve les articles sur...')\n"
    "- transcribe_audio : quand l'utilisateur fournit un fichier audio à transcrire "
    "('transcris ce fichier', 'analyse cet audio', 'que dit cet enregistrement')\n"
    "- analyze_image : quand l'utilisateur fournit une image à analyser "
    "('analyse cette image', 'extrais les infos de cette facture', 'que montre cette photo')\n"
    "- reponse_directe : pour les salutations, questions générales sans besoin d'outil\n"
    "En cas de doute entre search_web et search_articles : "
    "search_articles si la question porte sur l'historique de veille, "
    "search_web si elle porte sur l'actualité récente.\n"
    "Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après."
)


# ---------------------------------------------------------------------------
# Étape 1 — Raisonnement : choisir l'outil
# ---------------------------------------------------------------------------
def choisir_outil(requete: str) -> dict:
    """Demande au LLM quel outil utiliser pour répondre à la requête."""
    decision = appeler_llm_json(
        question=f"Requête de l'utilisateur : {requete}",
        schema=SCHEMA_DECISION,
        system_prompt=SYSTEM_REACT,
    )
    logger.info(f"[ReAct] Intent détecté    : {decision.get('intent', '?')}")
    logger.info(f"[ReAct] Outil choisi      : {decision.get('outil', '?')}")
    logger.info(f"[ReAct] Raisonnement      : {decision.get('raisonnement', '?')}")
    return decision


# ---------------------------------------------------------------------------
# Étape 2 — Action : exécuter l'outil choisi
# ---------------------------------------------------------------------------
def executer_outil(decision: dict) -> str:
    """Exécute l'outil indiqué dans la décision et retourne le résultat en texte."""
    outil = decision.get("outil", "reponse_directe")

    if outil == "query_db":
        sql = decision.get("sql", "SELECT * FROM clients")
        sql_ok, sql_msg = valider_sql(sql)
        if not sql_ok:
            resultat = f"[ERREUR_SECURITE] {sql_msg}"
            logger.warning(f"[ReAct] SQL bloqué par security : {sql}")
            return resultat
        try:
            lignes = query_db(sql)
            if not lignes:
                resultat = "[AUCUN_RESULTAT] La requête n'a retourné aucune donnée."
                logger.info("[ReAct] query_db : 0 ligne retournée.")
            else:
                resultat = json.dumps(lignes, ensure_ascii=False, indent=2)
                logger.info(f"[ReAct] Résultat query_db : {len(lignes)} ligne(s)")
        except (ValueError, RuntimeError) as e:
            # Correction Log B : marquer explicitement l'erreur pour éviter l'hallucination
            resultat = f"[ERREUR_OUTIL] La requête SQL a échoué : {e}"
            logger.error(f"[ReAct] {resultat}")

    elif outil == "search_web":
        query = decision.get("query_recherche", "")
        resultats = search_web(query)
        resultat = json.dumps(resultats, ensure_ascii=False, indent=2)
        logger.info(f"[ReAct] Résultat search_web : {len(resultats)} résultat(s)")

    elif outil == "search_articles":
        query = decision.get("query_recherche", "")
        try:
            resultats = rechercher_articles(query, n=5)
            if not resultats:
                resultat = "[AUCUN_RESULTAT] Aucun article archivé ne correspond à cette requête."
            else:
                resultat = json.dumps(resultats, ensure_ascii=False, indent=2)
            logger.info(f"[ReAct] Résultat search_articles (RAG) : {len(resultats)} résultat(s)")
        except Exception as e:
            resultat = f"[ERREUR_OUTIL] Recherche sémantique échouée : {e}"
            logger.error(f"[ReAct] {resultat}")

    elif outil == "transcribe_audio":
        fichier = decision.get("file_path", "")
        try:
            result = transcrire_audio(fichier)
            resultat = (
                f"**Transcription :**\n{result['transcription']}\n\n"
                f"**Analyse :**\n{result['analyse']}"
            )
            logger.info(f"[ReAct] Résultat transcribe_audio : {len(result['transcription'])} car.")
        except (FileNotFoundError, ValueError) as e:
            resultat = f"[ERREUR_OUTIL] Transcription impossible : {e}"
            logger.error(f"[ReAct] {resultat}")
        except RuntimeError as e:
            resultat = f"[ERREUR_OUTIL] Erreur API Whisper : {e}"
            logger.error(f"[ReAct] {resultat}")

    elif outil == "analyze_image":
        fichier = decision.get("file_path", "")
        consigne = decision.get("query_recherche", None) or None
        try:
            result = analyser_image(fichier, consigne=consigne)
            resultat = json.dumps(result, ensure_ascii=False, indent=2)
            logger.info(f"[ReAct] Résultat analyze_image : {len(result)} clé(s) extraites")
        except (FileNotFoundError, ValueError) as e:
            resultat = f"[ERREUR_OUTIL] Analyse image impossible : {e}"
            logger.error(f"[ReAct] {resultat}")
        except RuntimeError as e:
            resultat = f"[ERREUR_OUTIL] Erreur GPT-4o Vision : {e}"
            logger.error(f"[ReAct] {resultat}")

    else:  # reponse_directe
        resultat = "(aucun outil — réponse directe du LLM)"
        logger.info("[ReAct] Outil : réponse directe, pas d'exécution d'outil.")

    return resultat


# ---------------------------------------------------------------------------
# Étape 3 — Observation : formuler la réponse finale
# ---------------------------------------------------------------------------
def formuler_reponse(requete: str, resultat_outil: str) -> str:
    """Demande au LLM de formuler une réponse finale à partir du résultat de l'outil."""
    # Correction Log B : instruction stricte si l'outil a échoué ou retourné vide
    if resultat_outil.startswith("[ERREUR_OUTIL]"):
        instruction = (
            "L'outil a retourné une erreur. "
            "Informe l'utilisateur que la donnée est inaccessible. "
            "N'invente AUCUN chiffre, nom ou donnée — dis clairement que tu ne sais pas."
        )
    elif resultat_outil.startswith("[AUCUN_RESULTAT]"):
        instruction = (
            "L'outil n'a trouvé aucune donnée correspondante. "
            "Informe l'utilisateur qu'aucun résultat n'existe pour sa requête."
        )
    else:
        instruction = "Formule une réponse claire et concise en français pour l'utilisateur."

    prompt = (
        f"Requête initiale : {requete}\n\n"
        f"Résultat de l'outil :\n{resultat_outil}\n\n"
        f"{instruction}"
    )
    return appeler_llm(prompt)


# ---------------------------------------------------------------------------
# Boucle ReAct principale
# ---------------------------------------------------------------------------
MAX_ITERATIONS = 2  # Correction Log C : limite de boucle pour éviter les boucles infinies

def agent_react(requete: str) -> str:
    """
    Boucle ReAct complète : Reason → Act → Observe → Respond.
    Inclut une garde contre les boucles infinies (MAX_ITERATIONS).

    Args:
        requete: La question ou demande de l'utilisateur.

    Returns:
        Réponse finale en langage naturel.
    """
    print(f"\n{'='*60}")
    print(f"REQUÊTE : {requete}")
    print("=" * 60)

    # --- Garde de sécurité (M4E5) ---
    check = analyser_securite(requete)
    if check["bloque"]:
        msg = f"[BLOQUÉ] {check['raison']} (type: {check['type']})"
        logger.warning(f"[SECURITE] {msg}")
        print(f"\nRÉPONSE :\n{check['raison']}\n")
        return check["raison"]

    outils_essayes = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info(f"[ReAct] Itération {iteration}/{MAX_ITERATIONS}")

        decision = choisir_outil(requete)
        outil    = decision.get("outil", "reponse_directe")

        # Correction Log C : si le même outil échoue deux fois, basculer en réponse directe
        if outil in outils_essayes:
            logger.warning(f"[ReAct] Outil '{outil}' déjà essayé — abandon, réponse directe.")
            reponse = appeler_llm(
                f"Réponds à cette question en reconnaissant tes limites si nécessaire : {requete}"
            )
            break
        outils_essayes.append(outil)

        resultat = executer_outil(decision)

        # Si l'outil retourne une erreur et qu'il reste des itérations, on réessaie
        if resultat.startswith("[ERREUR_OUTIL]") and iteration < MAX_ITERATIONS:
            logger.warning(f"[ReAct] Itération {iteration} — outil en erreur, nouvelle tentative.")
            continue

        reponse = formuler_reponse(requete, resultat)
        break
    else:
        logger.error("[ReAct] Max itérations atteint — abandon.")
        reponse = "Je n'ai pas pu répondre à votre requête après plusieurs tentatives."

    # --- Filtrage de sortie (M4E5) : masquer données sensibles ---
    reponse = filtrer_sortie(reponse)

    logger.info("[ReAct] Réponse finale générée.")
    print(f"\nRÉPONSE :\n{reponse}\n")
    return reponse


# ---------------------------------------------------------------------------
# Test de connexion LLM (exercice 1)
# ---------------------------------------------------------------------------
def test_connexion_llm():
    """Test minimal : vérifie que l'appel LLM fonctionne."""
    print("=" * 60)
    print("Test de connexion à l'API OpenAI")
    print("=" * 60)
    try:
        from llm import appeler_llm
        reponse = appeler_llm("Bonjour, présente-toi en une phrase.")
        print(f"\nRéponse du modèle :\n{reponse}\n")
        print("Connexion OK.")
    except ValueError as e:
        print(f"Erreur de configuration : {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Erreur réseau/API : {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Exercice 3 — Tests de la boucle ReAct
    cas_tests = [
        "Tous les clients Premium",
        "Bonjour",
        "Tendances IA 2026",
    ]
    for requete in cas_tests:
        agent_react(requete)

    # Exercice 4 — Tests multimodaux (décommenter avec vos fichiers)
    # agent_react("Transcris ce fichier audio : data/sample.mp3")
    # agent_react("Analyse cette facture : data/facture.jpg")
