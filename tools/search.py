"""
Outil de récupération et filtrage des flux RSS.
"""
import feedparser
import logging
from datetime import datetime, timezone
from config import RSS_SOURCES, THEMES

logger = logging.getLogger(__name__)


def recuperer_articles_rss(sources: list[str] = None) -> list[dict]:
    """
    Lit tous les flux RSS et retourne les articles bruts.

    Returns:
        Liste de dicts avec: titre, lien, resume, date_publication, source
    """
    if sources is None:
        sources = RSS_SOURCES

    articles = []
    for url in sources:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Flux RSS malformé ({url}) : {feed.bozo_exception}")

            for entry in feed.entries:
                articles.append({
                    "titre": entry.get("title", "Sans titre"),
                    "lien": entry.get("link", ""),
                    "resume_brut": entry.get("summary", entry.get("description", "")),
                    "date_publication": _parse_date(entry),
                    "source": feed.feed.get("title", url),
                    "source_url": url,
                })
            logger.info(f"RSS {url} : {len(feed.entries)} articles récupérés.")
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du flux {url} : {e}")

    return articles


def filtrer_par_theme(articles: list[dict], themes: list[str] = None) -> list[dict]:
    """
    Filtre les articles dont le titre ou le résumé contient au moins un thème.

    Returns:
        Sous-liste d'articles pertinents thématiquement.
    """
    if themes is None:
        themes = THEMES

    themes_lower = [t.lower() for t in themes]
    filtrés = []

    for article in articles:
        texte = (article["titre"] + " " + article["resume_brut"]).lower()
        if any(theme in texte for theme in themes_lower):
            filtrés.append(article)

    logger.info(f"Filtrage thématique : {len(filtrés)}/{len(articles)} articles retenus.")
    return filtrés


def search_web(query: str) -> list[dict]:
    """
    Simule une recherche web et retourne des résultats fictifs cohérents
    avec la requête. Utilisé par l'agent ReAct pour l'intent 'search'.

    Args:
        query: La requête de recherche.

    Returns:
        Liste de dicts avec: titre, url, extrait.
    """
    logger.info(f"[search_web] Recherche simulée : '{query}'")

    query_lower = query.lower()

    banque = [
        {
            "mots_cles": ["ia", "intelligence artificielle", "llm", "gpt", "mistral", "gemini"],
            "resultats": [
                {
                    "titre": "Les LLMs en 2026 : où en sommes-nous ?",
                    "url": "https://example.com/llm-2026",
                    "extrait": "Les grands modèles de langage atteignent de nouveaux niveaux de performance en raisonnement multi-étapes. GPT-5 et Gemini Ultra 2 dominent les benchmarks.",
                },
                {
                    "titre": "IA générative : les tendances du marché enterprise",
                    "url": "https://example.com/ia-enterprise-2026",
                    "extrait": "L'adoption de l'IA générative en entreprise dépasse 60% dans le secteur IT. Les cas d'usage principaux : automatisation du code, veille, support client.",
                },
            ],
        },
        {
            "mots_cles": ["gpu", "nvidia", "amd", "puce", "chip", "matériel", "hardware"],
            "resultats": [
                {
                    "titre": "NVIDIA annonce sa nouvelle architecture Blackwell Ultra",
                    "url": "https://example.com/nvidia-blackwell-ultra",
                    "extrait": "NVIDIA présente des puces offrant 4x les performances d'inférence de la génération précédente, ciblant les datacenters IA.",
                },
            ],
        },
        {
            "mots_cles": ["cloud", "aws", "azure", "gcp", "kubernetes", "infrastructure"],
            "resultats": [
                {
                    "titre": "Cloud 2026 : la bataille des hyperscalers continue",
                    "url": "https://example.com/cloud-hyperscalers-2026",
                    "extrait": "AWS, Azure et GCP intensifient leurs offres IA managées. Les coûts d'inférence baissent de 40% sur un an.",
                },
            ],
        },
        {
            "mots_cles": ["cybersécurité", "sécurité", "faille", "ransomware", "hack", "zero-day"],
            "resultats": [
                {
                    "titre": "Cybersécurité : les attaques assistées par IA en hausse de 200%",
                    "url": "https://example.com/cybersecu-ia-2026",
                    "extrait": "Les acteurs malveillants utilisent des LLMs pour automatiser la génération de phishing et de malwares. Les SOCs répondent avec des outils de détection IA.",
                },
            ],
        },
    ]

    for groupe in banque:
        if any(mot in query_lower for mot in groupe["mots_cles"]):
            logger.info(f"[search_web] {len(groupe['resultats'])} résultat(s) trouvé(s).")
            return groupe["resultats"]

    # Résultat générique si aucun mot-clé ne correspond
    logger.info("[search_web] Aucun mot-clé reconnu, résultat générique retourné.")
    return [
        {
            "titre": f"Résultats pour : {query}",
            "url": "https://example.com/recherche-generique",
            "extrait": f"Aucun article spécifique trouvé pour '{query}' dans la base simulée.",
        }
    ]


def _parse_date(entry) -> str:
    """Extrait la date de publication d'une entrée RSS en ISO 8601."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()
