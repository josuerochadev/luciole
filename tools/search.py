"""
Outil de récupération et filtrage des flux RSS + recherche web (Tavily).
"""
import os
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
    Recherche web via l'API Tavily. Fallback sur une banque simulée
    si TAVILY_API_KEY n'est pas définie.

    Args:
        query: La requête de recherche.

    Returns:
        Liste de dicts avec: titre, url, extrait.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if api_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(query, max_results=5, search_depth="basic")
            resultats = []
            for r in response.get("results", []):
                resultats.append({
                    "titre": r.get("title", "Sans titre"),
                    "url": r.get("url", ""),
                    "extrait": r.get("content", ""),
                })
            logger.info(f"[search_web] Tavily : {len(resultats)} résultat(s) pour '{query}'.")
            return resultats
        except Exception as e:
            logger.error(f"[search_web] Erreur Tavily, fallback simulé : {e}")

    return _search_web_simule(query)


def _search_web_simule(query: str) -> list[dict]:
    """
    Fallback quand TAVILY_API_KEY est absente.
    Retourne une liste vide pour signaler l'indisponibilité.
    """
    logger.warning(f"[search_web] TAVILY_API_KEY absente — aucun résultat réel pour : '{query}'")
    return []


def _parse_date(entry) -> str:
    """Extrait la date de publication d'une entrée RSS en ISO 8601."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()
