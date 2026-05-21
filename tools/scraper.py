"""
Scraper d'articles web — extraction du contenu textuel complet.
Utilise trafilatura (rapide, gère bien la presse tech).
Fallback sur le résumé RSS si le scraping échoue.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import trafilatura
from trafilatura.settings import use_config

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 5000
SCRAPE_TIMEOUT = 8  # secondes par requête HTTP
MAX_WORKERS = 8
BATCH_TIMEOUT = 300  # 5 min max pour tout le batch (sécurité build Docker)

# Config trafilatura avec timeout HTTP
_traf_config = use_config()
_traf_config.set("DEFAULT", "DOWNLOAD_TIMEOUT", str(SCRAPE_TIMEOUT))


def scraper_article(url: str) -> str | None:
    if not url:
        return None
    try:
        html = trafilatura.fetch_url(url, config=_traf_config)
        if not html:
            return None
        texte = trafilatura.extract(html, include_comments=False, include_tables=False)
        if texte:
            return texte[:MAX_CONTENT_LENGTH]
        return None
    except Exception as e:
        logger.debug(f"[scraper] Échec pour {url} : {e}")
        return None


def scraper_articles_batch(articles: list[dict], batch_timeout: int = BATCH_TIMEOUT) -> list[dict]:
    total = len(articles)
    succes = 0
    deadline = time.monotonic() + batch_timeout

    def _scrape_one(idx_article):
        idx, article = idx_article
        contenu = scraper_article(article.get("lien", ""))
        return idx, contenu

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_scrape_one, (i, a)): i for i, a in enumerate(articles)}
        for future in as_completed(futures):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(f"[scraper] Timeout global ({batch_timeout}s) atteint, arrêt du batch.")
                for f in futures:
                    f.cancel()
                break
            try:
                idx, contenu = future.result(timeout=min(remaining, SCRAPE_TIMEOUT + 2))
                if contenu:
                    articles[idx]["contenu_complet"] = contenu
                    succes += 1
            except Exception as e:
                logger.debug(f"[scraper] Thread error : {e}")

    logger.info(f"[scraper] {succes}/{total} articles scrapés avec succès.")
    return articles
