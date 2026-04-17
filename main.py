"""
Point d'entrée de l'agent de veille technologique.
Exercice 3 : boucle ReAct (Reason + Act).

Utilisation : python main.py
"""
import json
import logging
import sys

from llm import appeler_llm, appeler_llm_json, appeler_llm_tools
from tools.search import search_web
from tools.database import query_db
from tools.rag import rechercher_articles
from tools.transcribe import transcrire_audio
from tools.vision import analyser_image
from tools.email import selectionner_articles, envoyer_rapport
from memory.store import store as memory_store, recall as memory_recall
from security import analyser_securite, valider_sql, filtrer_sortie
from monitoring import mark_fallback
from tracing import observe, update_current_trace, flush

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools OpenAI pour la décision ReAct (function calling natif)
# ---------------------------------------------------------------------------
TOOLS_DECISION = [
    {
        "type": "function",
        "function": {
            "name": "choisir_outil",
            "description": "Choisit l'outil à utiliser pour répondre à la requête utilisateur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": ["database", "search", "rag", "transcribe", "vision", "email", "general"],
                        "description": "Type de requête détecté.",
                    },
                    "outil": {
                        "type": "string",
                        "enum": [
                            "query_db",
                            "search_web",
                            "search_articles",
                            "transcribe_audio",
                            "analyze_image",
                            "preview_digest",
                            "send_digest",
                            "reponse_directe",
                        ],
                        "description": "Outil sélectionné pour traiter la requête.",
                    },
                    "sql": {
                        "type": "string",
                        "description": "Requête SQL si intent=database, sinon chaîne vide.",
                    },
                    "query_recherche": {
                        "type": "string",
                        "description": "Requête de recherche si intent=search ou rag, sinon chaîne vide.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Chemin du fichier si intent=transcribe ou vision, sinon chaîne vide.",
                    },
                    "raisonnement": {
                        "type": "string",
                        "description": "Explication courte du choix de l'outil.",
                    },
                },
                "required": ["intent", "outil", "raisonnement"],
                "additionalProperties": False,
            },
        },
    }
]

SYSTEM_REACT = (
    "Tu es Luciole, un agent de veille technologique spécialisé dans : "
    "IA, cybersécurité, cloud, infrastructure, DevOps, data et open source.\n\n"
    "PÉRIMÈTRE STRICT :\n"
    "- Tu ne traites QUE les sujets liés à la tech / informatique / numérique.\n"
    "- Si la requête est hors périmètre (recettes, sport, météo, santé, etc.), "
    "choisis reponse_directe et explique poliment que tu es un agent de veille "
    "technologique et que tu ne peux pas aider sur ce sujet. Propose de reformuler "
    "vers un sujet tech si possible.\n\n"
    "OUTILS :\n"
    "- query_db → données internes : clients, tickets, stats, KPIs (SQL)\n"
    "- search_web → actus, tendances, nouveautés, veille externe tech\n"
    "- search_articles → archives internes déjà collectées (RAG)\n"
    "- transcribe_audio → fichier audio fourni par l'utilisateur\n"
    "- analyze_image → image fournie par l'utilisateur\n"
    "- preview_digest → prévisualiser le digest email (résumé des articles, nombre, catégories)\n"
    "- send_digest → envoyer le digest par email aux destinataires configurés\n"
    "- reponse_directe → salutations, questions générales, OU requêtes hors périmètre\n\n"
    "ARBITRAGE preview_digest vs send_digest :\n"
    "- « montre / prévisualise / résume / aperçu / affiche le digest » → preview_digest\n"
    "- « envoie-moi un aperçu » ou « envoie un aperçu » → preview_digest (le mot « aperçu » prime sur « envoie »)\n"
    "- « envoie / expédie le digest / rapport par mail » (sans « aperçu ») → send_digest\n"
    "- En cas de doute entre preview et send → preview_digest (plus sûr)\n\n"
    "ARBITRAGE search_web vs search_articles :\n"
    "- Actus / tendances / briefing / récent → search_web\n"
    "- « archives », « historique », « déjà collectés » explicite → search_articles\n"
    "- Doute → search_web en priorité\n\n"
    "SOURCES : RSS archivés (search_articles), recherche web "
    "(IA, Cloud, Cybersécurité, GPU, etc.), SQLite interne (query_db). "
    "Pas d'accès académique, temps réel ou payant."
)


# ---------------------------------------------------------------------------
# Étape 1 — Raisonnement : choisir l'outil (function calling natif)
# ---------------------------------------------------------------------------
@observe(name="choisir_outil")
def choisir_outil(requete: str, historique: list[dict] | None = None) -> dict:
    """Demande au LLM quel outil utiliser via function calling natif OpenAI."""
    messages = [{"role": "system", "content": SYSTEM_REACT}]
    # Injecter l'historique conversationnel pour garder le contexte
    if historique:
        messages.extend(historique)
    messages.append({"role": "user", "content": f"Requête de l'utilisateur : {requete}"})
    decision = appeler_llm_tools(messages=messages, tools=TOOLS_DECISION)
    logger.info(f"[ReAct] Intent détecté    : {decision.get('intent', '?')}")
    logger.info(f"[ReAct] Outil choisi      : {decision.get('outil', '?')}")
    logger.info(f"[ReAct] Raisonnement      : {decision.get('raisonnement', '?')}")
    return decision


# ---------------------------------------------------------------------------
# Étape 2 — Action : exécuter l'outil choisi
# ---------------------------------------------------------------------------
@observe(name="executer_outil")
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

    elif outil == "preview_digest":
        try:
            articles = selectionner_articles(nb_max=20)
            if not articles:
                resultat = "[AUCUN_RESULTAT] Aucun article pertinent disponible pour le digest."
            else:
                # Résumé structuré pour le LLM
                categories = {}
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
                resultat = json.dumps(resume, ensure_ascii=False, indent=2)
            logger.info(f"[ReAct] Résultat preview_digest : {len(articles)} article(s)")
        except Exception as e:
            resultat = f"[ERREUR_OUTIL] Prévisualisation du digest échouée : {e}"
            logger.error(f"[ReAct] {resultat}")

    elif outil == "send_digest":
        try:
            result = envoyer_rapport(dry_run=False)
            resultat = json.dumps(result, ensure_ascii=False, indent=2)
            logger.info(f"[ReAct] Résultat send_digest : {result.get('message', '?')}")
        except Exception as e:
            resultat = f"[ERREUR_OUTIL] Envoi du digest échoué : {e}"
            logger.error(f"[ReAct] {resultat}")

    else:  # reponse_directe
        resultat = (
            "(aucun outil — réponse directe du LLM)\n"
            "Rappel : tu es Luciole, agent de veille technologique. "
            "Si la requête est hors périmètre tech, recadre poliment."
        )
        logger.info("[ReAct] Outil : réponse directe, pas d'exécution d'outil.")

    return resultat


# ---------------------------------------------------------------------------
# Étape 3 — Observation : formuler la réponse finale
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Instructions de formatage par type d'intent
# ---------------------------------------------------------------------------
_REGLES_FIDELITE = (
    "\nRÈGLES IMPÉRATIVES DE FIDÉLITÉ :\n"
    "1. **Ne JAMAIS inventer** un titre d'article, une URL, un chiffre, une date, "
    "un nom propre ou une statistique qui ne figure pas dans le résultat de l'outil.\n"
    "2. **Corriger les fausses prémisses** : si la question contient une affirmation "
    "que le résultat contredit, dis-le explicitement.\n"
    "3. **Clarification sur question ambiguë** : si la requête est vague, propose "
    "2 interprétations possibles ou demande une précision.\n"
    "4. **Nombre d'éléments** : si l'utilisateur demande N éléments mais que tu n'en as "
    "que M < N, annonce-le et ne présente que les M résultats réels."
)

_FORMAT_SEARCH = (
    "FORMAT DE RÉPONSE (Markdown) :\n"
    "1. Commence par une phrase de synthèse TL;DR (1-2 phrases résumant l'essentiel).\n"
    "2. Puis une section détaillée avec des bullet points `- **Titre** : description`.\n"
    "3. Termine TOUJOURS par un bloc sources :\n"
    "   `### Sources`\n"
    "   `- [Titre](URL)` pour chaque source citée.\n"
    "Utilise **gras** pour les points clés, et structure avec des titres `##` si pertinent."
)

_FORMAT_DATABASE = (
    "FORMAT DE RÉPONSE (Markdown) :\n"
    "1. Commence par une phrase de synthèse TL;DR résumant le résultat (ex : « 12 clients Premium trouvés »).\n"
    "2. Présente les données sous forme de liste structurée ou tableau Markdown.\n"
    "3. Mets en **gras** les chiffres clés et les valeurs importantes.\n"
    "4. Si pertinent, ajoute une observation ou tendance visible dans les données."
)

_FORMAT_RAG = (
    "FORMAT DE RÉPONSE (Markdown) :\n"
    "1. Commence par une phrase de synthèse TL;DR.\n"
    "2. Présente chaque article pertinent avec :\n"
    "   - **Titre** et score de pertinence\n"
    "   - Résumé en 1-2 phrases\n"
    "3. Termine TOUJOURS par un bloc sources :\n"
    "   `### Sources`\n"
    "   `- [Titre](URL)` pour chaque article cité.\n"
    "Utilise **gras** pour les points clés."
)

_FORMAT_DIRECT = (
    "Réponds de manière conversationnelle, concise et naturelle en français. "
    "Pas besoin de structure lourde — une réponse courte et directe suffit."
)

_FORMAT_MULTIMODAL = (
    "FORMAT DE RÉPONSE (Markdown) :\n"
    "1. Commence par une phrase de synthèse de ce qui a été analysé.\n"
    "2. Détaille les éléments clés extraits avec des bullet points.\n"
    "3. Utilise **gras** pour les informations importantes."
)

_FORMAT_EMAIL = (
    "FORMAT DE RÉPONSE (Markdown) :\n"
    "1. Commence par un résumé TL;DR du digest (nombre d'articles, catégories couvertes).\n"
    "2. Liste les top articles avec leur catégorie et score de pertinence.\n"
    "3. Si c'est un envoi, confirme le résultat (succès/échec, destinataires).\n"
    "Utilise **gras** pour les chiffres clés."
)

_FORMATS_PAR_INTENT = {
    "search": _FORMAT_SEARCH,
    "database": _FORMAT_DATABASE,
    "rag": _FORMAT_RAG,
    "email": _FORMAT_EMAIL,
    "general": _FORMAT_DIRECT,
    "transcribe": _FORMAT_MULTIMODAL,
    "vision": _FORMAT_MULTIMODAL,
}


@observe(name="formuler_reponse")
def formuler_reponse(requete: str, resultat_outil: str, intent: str = "general", historique: list[dict] | None = None) -> str:
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

    prompt = (
        f"Requête initiale : {requete}\n\n"
        f"Résultat de l'outil :\n{resultat_outil}\n\n"
        f"{instruction}"
    )
    return appeler_llm(prompt, historique=historique)


# ---------------------------------------------------------------------------
# Boucle ReAct principale
# ---------------------------------------------------------------------------
MAX_ITERATIONS = 2  # Correction Log C : limite de boucle pour éviter les boucles infinies

@observe(name="agent_react")
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

    # Langfuse : taguer la trace avec la requête utilisateur
    update_current_trace(input=requete, tags=["react-agent"])

    # --- Garde de sécurité (M4E5) ---
    check = analyser_securite(requete)
    if check["bloque"]:
        msg = f"[BLOQUÉ] {check['raison']} (type: {check['type']})"
        logger.warning(f"[SECURITE] {msg}")
        mark_fallback(f"security:{check.get('type', 'inconnu')}")
        print(f"\nRÉPONSE :\n{check['raison']}\n")
        return check["raison"]

    # --- Mémoire conversationnelle : rappeler l'historique ---
    historique = memory_recall(n=20)
    memory_store(requete, role="user")

    outils_essayes = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info(f"[ReAct] Itération {iteration}/{MAX_ITERATIONS}")

        decision = choisir_outil(requete, historique=historique)
        outil    = decision.get("outil", "reponse_directe")

        # Correction Log C : si le même outil échoue deux fois, basculer en réponse directe
        if outil in outils_essayes:
            logger.warning(f"[ReAct] Outil '{outil}' déjà essayé — abandon, réponse directe.")
            mark_fallback(f"outil_repete:{outil}")
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

        reponse = formuler_reponse(requete, resultat, intent=decision.get("intent", "general"), historique=historique)
        break
    else:
        logger.error("[ReAct] Max itérations atteint — abandon.")
        mark_fallback("max_iterations")
        reponse = "Je n'ai pas pu répondre à votre requête après plusieurs tentatives."

    # --- Filtrage de sortie (M4E5) : masquer données sensibles ---
    reponse = filtrer_sortie(reponse)

    # --- Mémoire conversationnelle : sauvegarder la réponse ---
    memory_store(reponse, role="assistant")

    logger.info("[ReAct] Réponse finale générée.")
    print(f"\nRÉPONSE :\n{reponse}\n")

    # Langfuse : flush des traces en fin de requête
    flush()

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
