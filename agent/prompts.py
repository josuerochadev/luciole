"""
Constantes de prompts, schémas d'outils et instructions de formatage
pour l'agent ReAct.
"""

# ---------------------------------------------------------------------------
# Schéma des outils pour la décision ReAct (function calling via Gemini)
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
                        "enum": ["database", "search", "rag", "vision", "email", "general"],
                        "description": "Type de requête détecté.",
                    },
                    "outil": {
                        "type": "string",
                        "enum": [
                            "query_db",
                            "search_web",
                            "search_articles",
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
                        "description": "Chemin du fichier si intent=vision, sinon chaîne vide.",
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
    "- query_db → base SQLite interne. Table unique disponible :\n"
    "  TABLE clients (id INTEGER PK, nom TEXT, email TEXT, type TEXT ['Premium'|'Standard'], depuis TEXT)\n"
    "  Contient quelques clients de test. Pas de tables tickets, stats ou KPIs.\n"
    "  Génère UNIQUEMENT des requêtes SELECT sur cette table.\n"
    "- search_web → actus, tendances, nouveautés, veille externe tech\n"
    "- search_articles → archives internes déjà collectées (RAG)\n"
    "- analyze_image → image ou PDF fourni par l'utilisateur\n"
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
    "Pas d'accès académique, temps réel ou payant.\n\n"
    "CONTEXTE CONVERSATIONNEL :\n"
    "- L'historique de la conversation est fourni dans les messages précédents.\n"
    "- Utilise-le pour résoudre les références implicites (« il », « ça », « le même », etc.).\n"
    "- Si l'utilisateur dit « et en cybersécurité ? », reprends le contexte de sa question précédente.\n"
    "- Ne redemande pas une information déjà fournie dans l'historique."
)

# ---------------------------------------------------------------------------
# Cascade M6E3 — classification de la complexité
# ---------------------------------------------------------------------------
PROMPT_COMPLEXITE = """Classe cette requête utilisateur.
Réponds UNIQUEMENT en JSON avec les clés complexite et categorie.
- complexite = simple si : salutation, FAQ, reformulation, lookup direct, question factuelle courte
- complexite = complexe si : raisonnement multi-étapes, synthèse, code, analyse comparative
- categorie = salutation | faq | raisonnement | code | analyse
Requête : {question}"""

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

_FORMATS_PAR_INTENT: dict[str, str] = {
    "search": _FORMAT_SEARCH,
    "database": _FORMAT_DATABASE,
    "rag": _FORMAT_RAG,
    "email": _FORMAT_EMAIL,
    "general": _FORMAT_DIRECT,
    "vision": _FORMAT_MULTIMODAL,
}

# Labels humains pour les outils (affichés côté client).
# Doit rester synchronisé avec l'enum "outil" de TOOLS_DECISION.
_TOOL_LABELS: dict[str, str] = {
    "query_db": "Interrogation de la base de données",
    "search_web": "Recherche sur le web",
    "search_articles": "Recherche dans les articles",
    "analyze_image": "Analyse d'image",
    "preview_digest": "Préparation du digest",
    "send_digest": "Envoi du digest",
    "reponse_directe": "Réflexion",
}
