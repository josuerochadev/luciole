"""
Script de démarrage : enrichit les articles pré-collectés au build.

Lit data/articles_raw.json (généré par prebuild.py au build Docker),
enrichit via LLM, sauvegarde en SQLite et indexe dans le RAG.
Si articles_raw.json n'existe pas, lance le pipeline complet en fallback.

Usage : python startup.py (appelé par start.sh)
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import DATA_DIR, PERTINENCE_MIN
from llm import resumer_article
from tools.database import sauvegarder_articles, article_deja_traite

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

RAW_FILE = os.path.join(DATA_DIR, "articles_raw.json")
LLM_WORKERS = 5


def run():
    # Vérifier si les articles pré-collectés existent
    if not os.path.exists(RAW_FILE):
        print("[startup] Pas de cache prebuild — lancement du pipeline complet...")
        from pipeline import run as pipeline_run
        pipeline_run(no_email=True)
        return

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"[startup] {len(articles)} articles pré-collectés trouvés.")

    # Filtrer les articles déjà en base
    nouveaux = [a for a in articles if not article_deja_traite(a.get("lien", ""))]
    print(f"[startup] {len(nouveaux)} nouveaux articles à enrichir.")

    if not nouveaux:
        print("[startup] Rien à faire, base déjà à jour.")
        return

    # Enrichissement LLM parallèle
    print(f"[startup] Enrichissement LLM ({LLM_WORKERS} threads)...")

    def _enrichir(article: dict) -> dict | None:
        titre = article.get("titre", "")
        contenu = article.get("contenu_complet", article.get("resume_brut", ""))
        try:
            analyse = resumer_article(titre, contenu)
            pertinence = int(analyse.get("pertinence", 0))
            if pertinence < PERTINENCE_MIN:
                return None
            article.update({
                "resume": analyse.get("resume", contenu[:300]),
                "categorie": analyse.get("categorie", "Autre"),
                "pertinence": pertinence,
                "action": analyse.get("action", "lire"),
            })
            return article
        except Exception as e:
            logging.warning(f"Enrichissement échoué pour '{titre}' : {e}")
            article.setdefault("categorie", "Autre")
            article.setdefault("pertinence", 5)
            return article

    enrichis = []
    done = 0
    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as pool:
        futures = {pool.submit(_enrichir, a): a for a in nouveaux}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                enrichis.append(result)
            if done % 50 == 0:
                print(f"[startup] {done}/{len(nouveaux)} traités...")

    print(f"[startup] {len(enrichis)} articles enrichis et pertinents.")

    # Sauvegarde SQLite + indexation RAG
    nb = sauvegarder_articles(enrichis)
    print(f"[startup] {nb} articles sauvegardés et indexés.")


if __name__ == "__main__":
    run()
