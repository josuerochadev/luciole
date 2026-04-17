import json
import re
import openai
import time
import logging
from config import OPENAI_API_KEY, MODEL_DEFAULT, TEMPERATURE, MAX_TOKENS, SYSTEM_PROMPT

# Monitoring : hook optionnel — no-op si le module n'est pas présent (ex: tests isolés)
try:
    from monitoring import add_llm_usage
except ImportError:  # pragma: no cover
    def add_llm_usage(prompt_tokens: int, completion_tokens: int) -> None:
        pass

# Langfuse : instrumentation automatique du client OpenAI + décorateurs
try:
    from tracing import observe, _langfuse_enabled
    if _langfuse_enabled:
        from langfuse.openai import OpenAI as LangfuseOpenAI
    else:
        LangfuseOpenAI = None
except ImportError:
    LangfuseOpenAI = None
    def observe(*args, **kwargs):
        def passthrough(fn): return fn
        if args and callable(args[0]): return args[0]
        return passthrough

logger = logging.getLogger(__name__)

_client = None


def get_openai_client():
    """Initialise le client OpenAI au premier appel (lazy init).
    Si Langfuse est actif, utilise le wrapper instrumenté.
    Point d'accès unique — utilisé aussi par tools/rag.py."""
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ValueError(
                "Clé API OpenAI manquante. Définissez OPENAI_API_KEY dans le fichier .env "
                "ou via PowerShell : $env:OPENAI_API_KEY = 'sk-...'"
            )
        if LangfuseOpenAI is not None:
            _client = LangfuseOpenAI(api_key=OPENAI_API_KEY)
            logger.info("[Langfuse] Client OpenAI instrumenté.")
        else:
            _client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _client

# Schéma JSON métier de l'agent de veille technologique
SCHEMA_VEILLE = {
    "pertinence": "entier de 1 à 10 — pertinence pour la veille techno",
    "categorie": "IA | Cybersécurité | Cloud | Infrastructure | DevOps | Données | Hors-sujet | Autre",
    "resume": "résumé factuel en 2-3 phrases maximum",
    "action": "lire | archiver | ignorer",
}


@observe(name="appeler_llm_json")
def appeler_llm_json(question: str, schema: dict = None, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """
    Appelle le LLM en lui demandant de répondre UNIQUEMENT en JSON valide
    selon le schéma fourni. Tente json.loads() puis fallback regex.

    Args:
        question:      Le contenu à analyser.
        schema:        Dictionnaire décrivant les clés attendues et leur signification.
                       Si None, utilise SCHEMA_VEILLE par défaut.
        system_prompt: Prompt système de l'agent.

    Returns:
        dict parsé depuis la réponse du LLM.

    Raises:
        ValueError: Si la réponse ne contient aucun JSON exploitable.
    """
    if schema is None:
        schema = SCHEMA_VEILLE

    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
    prompt_systeme = (
        f"{system_prompt}\n\n"
        "RÈGLE ABSOLUE : tu réponds UNIQUEMENT avec un objet JSON valide, "
        "sans texte avant ni après, sans balises markdown."
    )
    prompt_utilisateur = (
        f"Analyse le message suivant et réponds en JSON en respectant exactement ce schéma :\n"
        f"{schema_str}\n\n"
        f"Message à analyser :\n{question}"
    )

    texte_brut = appeler_llm(prompt_utilisateur, system_prompt=prompt_systeme)

    # --- Tentative 1 : json.loads() direct ---
    try:
        return json.loads(texte_brut)
    except json.JSONDecodeError:
        logger.debug("json.loads() direct échoué, tentative fallback regex.")

    # --- Tentative 2 : nettoyer les balises markdown ```json ... ``` ---
    texte_propre = re.sub(r"```(?:json)?", "", texte_brut).strip().strip("`").strip()
    try:
        return json.loads(texte_propre)
    except json.JSONDecodeError:
        logger.debug("Nettoyage markdown insuffisant, tentative extraction regex.")

    # --- Tentative 3 : extraire le premier objet JSON {...} trouvé ---
    match = re.search(r"\{.*\}", texte_brut, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            logger.warning("Extraction regex a trouvé un bloc mais invalide.")

    # --- Fallback ultime : retourner une structure dégradée avec le texte brut ---
    logger.error(f"Impossible de parser la réponse LLM en JSON. Réponse brute : {texte_brut!r}")
    return {
        "pertinence": 0,
        "categorie": "Erreur",
        "resume": texte_brut[:300],
        "action": "ignorer",
        "_parsing_error": True,
    }


@observe(name="appeler_llm")
def appeler_llm(question: str, system_prompt: str = SYSTEM_PROMPT, retries: int = 3) -> str:
    """
    Appelle l'API OpenAI et retourne le texte généré.

    Args:
        question: Le message utilisateur à envoyer au modèle.
        system_prompt: Le prompt système (rôle de l'agent).
        retries: Nombre de tentatives en cas d'erreur temporaire.

    Returns:
        Le texte de la réponse du modèle.

    Raises:
        ValueError: Si la clé API est absente ou invalide.
        RuntimeError: Si toutes les tentatives échouent.
    """
    for tentative in range(1, retries + 1):
        try:
            response = get_openai_client().chat.completions.create(
                model=MODEL_DEFAULT,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                timeout=30,
            )
            # Monitoring M5E5 : report token usage (no-op hors requête API)
            usage = getattr(response, "usage", None)
            if usage is not None:
                add_llm_usage(
                    getattr(usage, "prompt_tokens", 0) or 0,
                    getattr(usage, "completion_tokens", 0) or 0,
                )
            return response.choices[0].message.content.strip()

        except openai.AuthenticationError as e:
            raise ValueError(f"Clé API invalide ou révoquée : {e}") from e

        except openai.RateLimitError as e:
            logger.warning(f"Rate limit atteint (tentative {tentative}/{retries}). Attente 10s...")
            if tentative < retries:
                time.sleep(10)
            else:
                raise RuntimeError("Rate limit persistant après plusieurs tentatives.") from e

        except openai.APITimeoutError as e:
            logger.warning(f"Timeout API (tentative {tentative}/{retries})...")
            if tentative < retries:
                time.sleep(5)
            else:
                raise RuntimeError("Timeout persistant après plusieurs tentatives.") from e

        except openai.APIConnectionError as e:
            logger.warning(f"Erreur de connexion (tentative {tentative}/{retries})...")
            if tentative < retries:
                time.sleep(5)
            else:
                raise RuntimeError("Impossible de joindre l'API OpenAI.") from e

        except openai.APIError as e:
            logger.error(f"Erreur API inattendue : {e}")
            raise RuntimeError(f"Erreur API OpenAI : {e}") from e


@observe(name="appeler_llm_tools")
def appeler_llm_tools(
    messages: list[dict],
    tools: list[dict],
    retries: int = 3,
) -> dict:
    """
    Appelle l'API OpenAI avec le function calling natif.

    Args:
        messages: Liste de messages (system + user).
        tools:    Liste de tools au format OpenAI (type: "function", ...).
        retries:  Nombre de tentatives en cas d'erreur temporaire.

    Returns:
        dict avec les arguments parsés du premier tool_call,
        ou {} si le modèle ne déclenche aucun tool_call.

    Raises:
        ValueError: Si la clé API est absente ou invalide.
        RuntimeError: Si toutes les tentatives échouent.
    """
    for tentative in range(1, retries + 1):
        try:
            response = get_openai_client().chat.completions.create(
                model=MODEL_DEFAULT,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                messages=messages,
                tools=tools,
                tool_choice="required",
                timeout=30,
            )
            usage = getattr(response, "usage", None)
            if usage is not None:
                add_llm_usage(
                    getattr(usage, "prompt_tokens", 0) or 0,
                    getattr(usage, "completion_tokens", 0) or 0,
                )

            message = response.choices[0].message
            if message.tool_calls:
                tc = message.tool_calls[0]
                return json.loads(tc.function.arguments)

            logger.warning("Le modèle n'a déclenché aucun tool_call.")
            return {}

        except openai.AuthenticationError as e:
            raise ValueError(f"Clé API invalide ou révoquée : {e}") from e

        except openai.RateLimitError as e:
            logger.warning(f"Rate limit atteint (tentative {tentative}/{retries}). Attente 10s...")
            if tentative < retries:
                time.sleep(10)
            else:
                raise RuntimeError("Rate limit persistant après plusieurs tentatives.") from e

        except openai.APITimeoutError as e:
            logger.warning(f"Timeout API (tentative {tentative}/{retries})...")
            if tentative < retries:
                time.sleep(5)
            else:
                raise RuntimeError("Timeout persistant après plusieurs tentatives.") from e

        except openai.APIConnectionError as e:
            logger.warning(f"Erreur de connexion (tentative {tentative}/{retries})...")
            if tentative < retries:
                time.sleep(5)
            else:
                raise RuntimeError("Impossible de joindre l'API OpenAI.") from e

        except openai.APIError as e:
            logger.error(f"Erreur API inattendue : {e}")
            raise RuntimeError(f"Erreur API OpenAI : {e}") from e


def resumer_article(titre: str, contenu: str) -> dict:
    """
    Résume un article RSS et retourne pertinence, catégorie, résumé et action.
    Délègue le parsing JSON à appeler_llm_json().
    """
    message = f"Titre : {titre}\n\nContenu : {contenu[:2000]}"
    return appeler_llm_json(message)
