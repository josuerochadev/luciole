"""
Pré-collecte RSS au build Docker (sans clé API).

Étapes exécutées :
  1. Collecte des flux RSS
  2. Filtrage thématique
  3. Dédoublonnage par titre
  4. Scraping du contenu complet

Le résultat est sauvegardé dans data/articles_raw.json.
L'enrichissement LLM (résumé, catégorie, pertinence) est fait au démarrage
via startup.py, car il nécessite OPENAI_API_KEY.

Usage : python prebuild.py
"""
import json
import os
from difflib import SequenceMatcher

from tools.search import recuperer_articles_rss, filtrer_par_theme
from tools.scraper import scraper_articles_batch
from config import DATA_DIR

TITRE_SIMILARITY_THRESHOLD = 0.85
RAW_FILE = os.path.join(DATA_DIR, "articles_raw.json")


def _dedoublonner_par_titre(articles: list[dict]) -> list[dict]:
    uniques = []
    titres_vus = []
    for article in articles:
        titre = article.get("titre", "").strip().lower()
        if not titre:
            uniques.append(article)
            continue
        doublon = False
        for t in titres_vus:
            if SequenceMatcher(None, titre, t).ratio() >= TITRE_SIMILARITY_THRESHOLD:
                doublon = True
                break
        if not doublon:
            titres_vus.append(titre)
            uniques.append(article)
    return uniques


def run():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Collecte RSS
    print("[prebuild] 1/4 Collecte RSS...")
    articles = recuperer_articles_rss()
    print(f"           {len(articles)} articles récupérés.")

    # 2. Filtrage thématique
    print("[prebuild] 2/4 Filtrage thématique...")
    filtres = filtrer_par_theme(articles)
    print(f"           {len(filtres)} articles retenus.")

    # 3. Dédoublonnage
    print("[prebuild] 3/4 Dédoublonnage...")
    uniques = _dedoublonner_par_titre(filtres)
    print(f"           {len(uniques)} articles uniques.")

    # 4. Scraping
    print("[prebuild] 4/4 Scraping du contenu complet...")
    scrapes = scraper_articles_batch(uniques)
    nb_ok = sum(1 for a in scrapes if a.get("contenu_complet"))
    print(f"           {nb_ok}/{len(scrapes)} articles scrapés.")

    # Sauvegarde
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(scrapes, f, ensure_ascii=False)
    print(f"[prebuild] {len(scrapes)} articles sauvegardés dans {RAW_FILE}")


if __name__ == "__main__":
    run()
