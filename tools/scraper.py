"""
Scraper d'articles web — extraction du contenu textuel complet.
Utilise trafilatura (rapide, gère bien la presse tech).
Fallback sur le résumé RSS si le scraping échoue.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import trafilatura

logger = logging.getLogger(__name__)

# Limite de caractères pour éviter les articles géants (livres blancs, etc.)
MAX_CONTENT_LENGTH = 5000
SCRAPE_TIMEOUT = 10  # secondes par article
MAX_WORKERS = 8  # threads parallèles pour le scraping


def scraper_article(url: str) -> str | None:
    """
    Extrait le contenu textuel principal d'une URL.

    Returns:
        Le texte extrait (tronqué à MAX_CONTENT_LENGTH), ou None si échec.
    """
    if not url:
        return None
    try:
        html = trafilatura.fetch_url(url)
        if not html:
            return None
        texte = trafilatura.extract(html, include_comments=False, include_tables=False)
        if texte:
            return texte[:MAX_CONTENT_LENGTH]
        return None
    except Exception as e:
        logger.debug(f"[scraper] Échec pour {url} : {e}")
        return None


def scraper_articles_batch(articles: list[dict]) -> list[dict]:
    """
    Enrichit une liste d'articles avec leur contenu complet (parallèle).
    Ajoute la clé 'contenu_complet' à chaque article.
    Si le scraping échoue, conserve le resume_brut existant.

    Args:
        articles: Liste de dicts avec au moins 'lien' et 'resume_brut'.

    Returns:
        La même liste, enrichie avec 'contenu_complet'.
    """
    total = len(articles)
    succes = 0

    def _scrape_one(idx_article):
        idx, article = idx_article
        contenu = scraper_article(article.get("lien", ""))
        return idx, contenu

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_scrape_one, (i, a)): i for i, a in enumerate(articles)}
        for future in as_completed(futures):
            try:
                idx, contenu = future.result(timeout=SCRAPE_TIMEOUT + 5)
                if contenu:
                    articles[idx]["contenu_complet"] = contenu
                    succes += 1
            except Exception as e:
                logger.debug(f"[scraper] Thread error : {e}")

    logger.info(f"[scraper] {succes}/{total} articles scrapés avec succès.")
    return articles
