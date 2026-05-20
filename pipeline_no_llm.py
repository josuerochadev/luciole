"""
Pipeline de sauvegarde rapide SANS enrichissement LLM.
Collecte RSS -> filtrage -> scraping -> sauvegarde directe en base.
Les articles seront enrichis plus tard quand le quota Gemini se reset.
"""
import json
import logging
from difflib import SequenceMatcher
from datetime import datetime, timezone

from tools.search import recuperer_articles_rss, filtrer_par_theme
from tools.scraper import scraper_articles_batch
from tools.database import article_deja_traite
from db_utils import connect, cursor

TITRE_SIMILARITY_THRESHOLD = 0.85
CACHE_FILE = "data/articles_scraped.json"

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")


def _dedoublonner_par_titre(articles: list[dict]) -> list[dict]:
    uniques, titres_vus = [], []
    for article in articles:
        titre = article.get("titre", "").strip().lower()
        if not titre:
            uniques.append(article)
            continue
        if not any(SequenceMatcher(None, titre, t).ratio() >= TITRE_SIMILARITY_THRESHOLD for t in titres_vus):
            titres_vus.append(titre)
            uniques.append(article)
    return uniques


def collecter_et_scraper() -> list[dict]:
    """Etapes 1-3 : collecte, filtrage, scraping. Sauvegarde en cache JSON."""
    print("\n[1/4] Collecte RSS...")
    articles = recuperer_articles_rss()
    print(f"      {len(articles)} articles recuperes.")

    print("[2/4] Filtrage thematique...")
    filtres = filtrer_par_theme(articles)
    print(f"      {len(filtres)} articles retenus.")

    nouveaux = [a for a in filtres if not article_deja_traite(a["lien"])]
    avant_dedup = len(nouveaux)
    nouveaux = _dedoublonner_par_titre(nouveaux)
    print(f"      {len(nouveaux)} nouveaux ({avant_dedup - len(nouveaux)} doublons supprimes).")

    print("[3/4] Scraping du contenu complet...")
    nouveaux = scraper_articles_batch(nouveaux)
    nb_scrapes = sum(1 for a in nouveaux if a.get("contenu_complet"))
    print(f"      {nb_scrapes}/{len(nouveaux)} articles scrapes.")

    # Enrichissement minimal sans LLM
    for a in nouveaux:
        a.setdefault("resume", a.get("resume_brut", ""))
        a.setdefault("categorie", "Non classe")
        a.setdefault("pertinence", 0)
        a.setdefault("action", "lire")

    # Sauvegarde cache JSON pour eviter de refaire le scraping si la DB plante
    import os
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(nouveaux, f, ensure_ascii=False)
    print(f"      Cache sauvegarde: {CACHE_FILE} ({len(nouveaux)} articles)")

    return nouveaux


def sauvegarder_en_base(articles: list[dict]) -> int:
    """Etape 4 : sauvegarde en base avec connexion fraiche."""
    print("[4/4] Sauvegarde en base (connexion fraiche)...")
    conn = connect()
    try:
        cur = cursor(conn)
        now = datetime.now(timezone.utc).isoformat()
        nb = 0
        for a in articles:
            lien = a.get("lien", "")
            if not lien:
                continue
            cur.execute(
                """
                INSERT INTO articles
                    (lien, titre, resume_brut, resume, contenu_complet, categorie,
                     pertinence, action, source, source_url, date_publication, date_ajout, archive)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                ON CONFLICT (lien) DO NOTHING
                """,
                (
                    lien,
                    a.get("titre", ""),
                    a.get("resume_brut", ""),
                    a.get("resume", ""),
                    a.get("contenu_complet", ""),
                    a.get("categorie", "Non classe"),
                    int(a.get("pertinence", 0)),
                    a.get("action", "lire"),
                    a.get("source", ""),
                    a.get("source_url", ""),
                    a.get("date_publication", ""),
                    now,
                ),
            )
            if cur.rowcount > 0:
                nb += 1
        conn.commit()
        print(f"      {nb} articles sauvegardes en base.")
        return nb
    finally:
        conn.close()


def run():
    articles = collecter_et_scraper()
    nb = sauvegarder_en_base(articles)
    print(f"\nTermine — {nb} articles en base.\n")
    return nb


def run_from_cache():
    """Recharge le cache JSON et sauvegarde en base (utile si la DB a plante)."""
    print(f"Chargement du cache {CACHE_FILE}...")
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)
    print(f"      {len(articles)} articles charges depuis le cache.")
    nb = sauvegarder_en_base(articles)
    print(f"\nTermine — {nb} articles en base.\n")
    return nb


if __name__ == "__main__":
    import sys
    if "--from-cache" in sys.argv:
        run_from_cache()
    else:
        run()
