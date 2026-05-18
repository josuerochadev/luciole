"""
Point d'entrée de l'agent de veille technologique.
Boucle ReAct (Reason + Act) — synchrone et streaming SSE.

Utilisation : python main.py
"""
import logging
import time
import uuid

from config import MAX_TOKENS_BY_INTENT
from llm import appeler_llm, appeler_llm_stream
from memory.store import store as memory_store, recall as memory_recall
from monitoring import mark_fallback
from security import analyser_securite, filtrer_sortie
from tracing import flush, observe, update_current_trace
from agent.cascade import classifier_complexite, choisir_modele
from agent.prompts import _TOOL_LABELS
from agent.response import _construire_prompt_reponse, formuler_reponse
from agent.tools_runner import choisir_outil, executer_outil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Limite de boucle pour éviter les boucles infinies (Correction Log C)
MAX_ITERATIONS = 2


# ---------------------------------------------------------------------------
# Boucle ReAct principale (synchrone)
# ---------------------------------------------------------------------------
@observe(name="agent_react")
def agent_react(requete: str, conversation_id: str | None = None) -> str:
    """
    Boucle ReAct complète : Reason → Act → Observe → Respond.

    Args:
        requete:         La question ou demande de l'utilisateur.
        conversation_id: ID de conversation pour isoler la mémoire par utilisateur.

    Returns:
        Réponse finale en langage naturel.
    """
    logger.info(f"[ReAct] Requête reçue : {requete[:200]}")
    update_current_trace(input=requete, tags=["react-agent"])

    # --- Cascade M6E3 : classifier la complexité ---
    routing = classifier_complexite(requete)
    model_cascade = choisir_modele(routing["complexite"])
    logger.info(
        f"[Cascade] complexite={routing['complexite']}, "
        f"categorie={routing.get('categorie', '?')}, model={model_cascade}"
    )

    # --- Garde de sécurité ---
    check = analyser_securite(requete)
    if check["bloque"]:
        logger.warning(f"[SECURITE] {check['raison']} (type: {check['type']})")
        mark_fallback(f"security:{check.get('type', 'inconnu')}")
        return check["raison"]

    # --- Mémoire conversationnelle ---
    effective_conv_id = conversation_id or str(uuid.uuid4())
    historique = memory_recall(n=20, conversation_id=effective_conv_id)
    memory_store(requete, role="user", conversation_id=effective_conv_id)

    outils_essayes: list[str] = []
    reponse = ""

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info(f"[ReAct] Itération {iteration}/{MAX_ITERATIONS}")

        decision = choisir_outil(requete, historique=historique, model=model_cascade)
        outil = decision.get("outil", "reponse_directe")

        # Détection boucle : même outil échoué deux fois → réponse directe
        if outil in outils_essayes:
            logger.warning(f"[ReAct] Outil '{outil}' déjà essayé — abandon, réponse directe.")
            mark_fallback(f"outil_repete:{outil}")
            reponse = appeler_llm(
                f"Réponds à cette question en reconnaissant tes limites si nécessaire : {requete}",
                model=model_cascade,
            )
            break
        outils_essayes.append(outil)

        resultat = executer_outil(decision)

        if resultat.startswith("[ERREUR_OUTIL]") and iteration < MAX_ITERATIONS:
            logger.warning(f"[ReAct] Itération {iteration} — outil en erreur, nouvelle tentative.")
            continue

        intent = decision.get("intent", "general")
        reponse = formuler_reponse(
            requete, resultat, intent=intent, historique=historique,
            model=model_cascade, max_tokens=MAX_TOKENS_BY_INTENT.get(intent),
        )
        break
    else:
        logger.error("[ReAct] Max itérations atteint — abandon.")
        mark_fallback("max_iterations")
        reponse = "Je n'ai pas pu répondre à votre requête après plusieurs tentatives."

    # --- Filtrage de sortie ---
    reponse = filtrer_sortie(reponse)

    # --- Sauvegarder la réponse en mémoire ---
    memory_store(reponse, role="assistant", conversation_id=effective_conv_id)
    logger.info("[ReAct] Réponse finale générée.")
    flush()

    return reponse


# ---------------------------------------------------------------------------
# Boucle ReAct streaming (SSE)
# ---------------------------------------------------------------------------
async def agent_react_stream(requete: str, conversation_id: str | None = None):
    """
    Version streaming de agent_react(). Générateur async qui yield des
    événements JSON pour le streaming SSE.

    Args:
        requete:         La question ou demande de l'utilisateur.
        conversation_id: ID de conversation pour isoler la mémoire par utilisateur.

    Yields:
        dict: Événements SSE avec type thinking/tool_result/chunk/done.
    """
    t0 = time.time()
    update_current_trace(input=requete, tags=["react-agent", "streaming"])

    # --- Cascade ---
    routing = classifier_complexite(requete)
    model_cascade = choisir_modele(routing["complexite"])
    logger.info(
        f"[Cascade] complexite={routing['complexite']}, "
        f"categorie={routing.get('categorie', '?')}, model={model_cascade}"
    )

    # --- Sécurité ---
    check = analyser_securite(requete)
    if check["bloque"]:
        logger.warning(f"[SECURITE] {check['raison']} (type: {check['type']})")
        mark_fallback(f"security:{check.get('type', 'inconnu')}")
        yield {"type": "chunk", "content": check["raison"]}
        yield {"type": "done", "latency_ms": int((time.time() - t0) * 1000), "full_response": check["raison"]}
        flush()
        return

    # --- Mémoire ---
    effective_conv_id = conversation_id or str(uuid.uuid4())
    historique = memory_recall(n=20, conversation_id=effective_conv_id)
    memory_store(requete, role="user", conversation_id=effective_conv_id)

    outils_essayes: list[str] = []
    resultat = ""

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info(f"[ReAct] Itération {iteration}/{MAX_ITERATIONS}")

        decision = choisir_outil(requete, historique=historique, model=model_cascade)
        outil = decision.get("outil", "reponse_directe")

        yield {
            "type": "thinking",
            "tool": outil,
            "label": _TOOL_LABELS.get(outil, outil),
        }

        # Détection boucle
        if outil in outils_essayes:
            logger.warning(f"[ReAct] Outil '{outil}' déjà essayé — abandon.")
            mark_fallback(f"outil_repete:{outil}")
            full = ""
            for chunk in appeler_llm_stream(
                f"Réponds à cette question en reconnaissant tes limites si nécessaire : {requete}",
                model=model_cascade,
            ):
                full += chunk
                yield {"type": "chunk", "content": chunk}
            resultat = full
            break
        outils_essayes.append(outil)

        resultat = executer_outil(decision)

        yield {
            "type": "tool_result",
            "tool": outil,
            "label": _TOOL_LABELS.get(outil, outil),
            "summary": resultat[:200] + ("…" if len(resultat) > 200 else ""),
        }

        if resultat.startswith("[ERREUR_OUTIL]") and iteration < MAX_ITERATIONS:
            logger.warning(f"[ReAct] Itération {iteration} — outil en erreur, retry.")
            continue

        # --- Stream la réponse finale ---
        intent = decision.get("intent", "general")
        prompt = _construire_prompt_reponse(requete, resultat, intent)
        full_response = ""
        for chunk in appeler_llm_stream(
            prompt, historique=historique,
            model=model_cascade, max_tokens=MAX_TOKENS_BY_INTENT.get(intent),
        ):
            full_response += chunk
            yield {"type": "chunk", "content": chunk}
        resultat = full_response
        break
    else:
        logger.error("[ReAct] Max itérations atteint — abandon.")
        mark_fallback("max_iterations")
        resultat = "Je n'ai pas pu répondre à votre requête après plusieurs tentatives."
        yield {"type": "chunk", "content": resultat}

    # --- Post-traitement ---
    reponse = filtrer_sortie(resultat)
    memory_store(reponse, role="assistant", conversation_id=effective_conv_id)

    latency_ms = int((time.time() - t0) * 1000)
    logger.info(f"[ReAct] Streaming terminé en {latency_ms}ms.")
    yield {"type": "done", "latency_ms": latency_ms, "full_response": reponse}
    flush()


# ---------------------------------------------------------------------------
# Point d'entrée CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cas_tests = [
        "Tous les clients Premium",
        "Bonjour",
        "Tendances IA 2026",
    ]
    for requete in cas_tests:
        agent_react(requete)
