"""
Module de securite pour l'agent de veille technologique.
Exercice M4E5 : detection d'injections, validation d'input, filtrage de sortie.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_INPUT_LENGTH = 2000

# Patterns de prompt injection (case-insensitive)
INJECTION_PATTERNS = [
    r"ignore\s+(toutes?\s+)?(tes|les|vos)\s+instructions",
    r"oublie\s+(toutes?\s+)?(tes|les|vos)\s+(instructions|regles|consignes)",
    r"tu\s+es\s+maintenant",
    r"you\s+are\s+now",
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(r[eé]p[eè]te|repets|affiche|montre|donne|copie).*system\s*prompt",
    r"(repeat|show|display|reveal|print).*system\s*prompt",
    r"instructions?\s+(cach[eé]es?|secr[eè]tes?|internes?|hidden)",
    r"(ton|tes|votre|vos)\s+system\s*prompt",
    r"INSTRUCTION\s+SYST[EÈ]ME\s+PRIORITAIRE",
    r"(override|bypass|disable)\s+(security|safety|filter|restriction)",
    r"jailbreak",
    r"DAN\s*mode",
    r"(ignore|disregard)\s+(the\s+)?(above|previous|prior)",
]

# Patterns SQL dangereux (dans le SQL genere par le LLM)
SQL_DANGEROUS_PATTERNS = [
    r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)\b",
    r"--",
    r"/\*",
    r"UNION\s+SELECT",
    r"OR\s+1\s*=\s*1",
    r"OR\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",
    r"xp_cmdshell",
    r"EXEC\s*\(",
]

# Patterns de donnees sensibles a masquer en sortie
# Ordre important : IBAN avant telephone (evite les faux positifs)
SENSITIVE_PATTERNS = [
    ("iban", r"\b[A-Z]{2}\d{2}(?:\s?[\dA-Z]{4}){2,7}(?:\s?\d{1,3})?\b", "[IBAN MASQUE]"),
    ("carte_bancaire", r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CB MASQUE]"),
    ("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL MASQUE]"),
    ("phone_fr", r"(?:(?:\+33|0)\s*[1-9])(?:[\s.-]*\d{2}){4}", "[TEL MASQUE]"),
]

# Actions non autorisees
UNAUTHORIZED_ACTION_PATTERNS = [
    r"envoie?\s+(un\s+)?e?-?mail\s+[àa]\s+tous",
    r"send\s+(an?\s+)?email\s+to\s+(all|everyone)",
    r"supprime[rz]?\s+(tous?\s+les?|la\s+base|toutes?\s+les?\s+donn[eé]es)",
    r"delete\s+(all|the\s+database|everything)",
    r"execute\s+(cette\s+)?commande\s+syst[eè]me",
]


# ---------------------------------------------------------------------------
# Validation de l'input
# ---------------------------------------------------------------------------
def valider_input(texte: str) -> tuple[bool, str]:
    """Valide l'input utilisateur : non vide, pas trop long."""
    if not texte or not texte.strip():
        return False, "L'input est vide."
    if len(texte) > MAX_INPUT_LENGTH:
        return False, f"L'input depasse la limite ({len(texte)}/{MAX_INPUT_LENGTH} caracteres)."
    return True, "OK"


# ---------------------------------------------------------------------------
# Detection de prompt injection
# ---------------------------------------------------------------------------
def detecter_injection(texte: str) -> tuple[bool, str]:
    """Detecte les tentatives de prompt injection dans l'input."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, texte, re.IGNORECASE):
            logger.warning(f"[SECURITE] Injection detectee — pattern: {pattern}")
            return True, pattern
    return False, ""


# ---------------------------------------------------------------------------
# Detection d'actions non autorisees
# ---------------------------------------------------------------------------
def detecter_action_non_autorisee(texte: str) -> tuple[bool, str]:
    """Detecte les demandes d'actions non autorisees (envoi de masse, suppression...)."""
    for pattern in UNAUTHORIZED_ACTION_PATTERNS:
        if re.search(pattern, texte, re.IGNORECASE):
            logger.warning(f"[SECURITE] Action non autorisee — pattern: {pattern}")
            return True, pattern
    return False, ""


# ---------------------------------------------------------------------------
# Validation SQL
# ---------------------------------------------------------------------------
def valider_sql(sql: str) -> tuple[bool, str]:
    """Valide une requete SQL generee par le LLM avant execution."""
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return False, f"Seules les requetes SELECT sont autorisees."
    for pattern in SQL_DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            logger.warning(f"[SECURITE] SQL dangereux — pattern: {pattern}, sql: {sql}")
            return False, "Requete SQL bloquee (pattern dangereux detecte)."
    return True, "OK"


# ---------------------------------------------------------------------------
# Filtrage de la sortie (donnees sensibles)
# ---------------------------------------------------------------------------
def filtrer_sortie(texte: str) -> str:
    """Masque les donnees sensibles (emails, telephones, IBAN, CB) dans la sortie."""
    resultat = texte
    for nom, pattern, remplacement in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, resultat)
        if matches:
            logger.info(f"[SECURITE] {len(matches)} {nom}(s) masque(s) dans la sortie.")
        resultat = re.sub(pattern, remplacement, resultat)
    return resultat


# ---------------------------------------------------------------------------
# Analyse complete — point d'entree principal
# ---------------------------------------------------------------------------
def analyser_securite(texte: str) -> dict:
    """
    Analyse complete de securite sur l'input utilisateur.

    Returns:
        dict: bloque (bool), raison (str), type (str)
    """
    ok, msg = valider_input(texte)
    if not ok:
        return {"bloque": True, "raison": msg, "type": "input_invalide"}

    injection, pattern = detecter_injection(texte)
    if injection:
        return {"bloque": True, "raison": "Tentative de prompt injection detectee.", "type": "injection"}

    non_autorise, pattern = detecter_action_non_autorisee(texte)
    if non_autorise:
        return {"bloque": True, "raison": "Action non autorisee detectee.", "type": "action_non_autorisee"}

    return {"bloque": False, "raison": "", "type": "ok"}
