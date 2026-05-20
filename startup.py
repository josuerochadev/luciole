"""
Script de démarrage : enrichit les articles pré-collectés au build.

Lit data/articles_raw.json (généré par prebuild.py au build Docker),
enrichit via LLM, sauvegarde en PostgreSQL et indexe dans le RAG.
Si articles_raw.json n'existe pas, lance le pipeline complet en fallback.
Reconstruit l'index RAG depuis la DB si embeddings.json est absent
(cas d'un redéploiement Railway sans volume persistant).

Usage : python startup.py (appelé par start.sh)
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import DATA_DIR
from tools.database import sauvegarder_articles, article_deja_traite
from tools.enrichment import enrichir_article

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

RAW_FILE = os.path.join(DATA_DIR, "articles_raw.json")
LLM_WORKERS = 5


def _db_has_articles() -> bool:
    """Verifie si la table articles contient au moins 1 article actif."""
    try:
        from tools.database import lire_articles_actifs
        return len(lire_articles_actifs()) > 0
    except Exception:
        return False


def run():
    # Cas 1 : articles pre-collectes au build (prebuild.py)
    if os.path.exists(RAW_FILE):
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)

        print(f"[startup] {len(articles)} articles pre-collectes trouves.")

        nouveaux = [a for a in articles if not article_deja_traite(a.get("lien", ""))]
        print(f"[startup] {len(nouveaux)} nouveaux articles a enrichir.")

        if not nouveaux:
            print("[startup] Rien a faire, base deja a jour.")
            return

        print(f"[startup] Enrichissement LLM ({LLM_WORKERS} threads)...")
        enrichis = []
        done = 0
        with ThreadPoolExecutor(max_workers=LLM_WORKERS) as pool:
            futures = {pool.submit(enrichir_article, a): a for a in nouveaux}
            for future in as_completed(futures):
                done += 1
                result = future.result()
                if result:
                    enrichis.append(result)
                if done % 50 == 0:
                    print(f"[startup] {done}/{len(nouveaux)} traites...")

        print(f"[startup] {len(enrichis)} articles enrichis et pertinents.")
        nb = sauvegarder_articles(enrichis)
        print(f"[startup] {nb} articles sauvegardes et indexes.")
        return

    # Cas 2 : pas de cache prebuild et DB vide -> pipeline complet
    if not _db_has_articles():
        print("[startup] DB vide et pas de cache prebuild — lancement du pipeline complet...")
        from pipeline import run as pipeline_run
        pipeline_run(no_email=True)
        return

    # Cas 3 : DB deja peuplee, rien a faire
    print("[startup] Base deja peuplee, pas de pipeline necessaire.")


def _rebuild_rag_if_needed() -> None:
    """
    Si l'index RAG (embeddings.json) est absent ou vide, reconstruit-le
    depuis tous les articles actifs en base (utile après un redéploiement
    sur Railway où data/ est éphémère sans volume persistant).
    """
    import os
    from config import DATA_DIR

    embeddings_file = os.path.join(DATA_DIR, "embeddings.json")
    if os.path.exists(embeddings_file) and os.path.getsize(embeddings_file) > 10:
        return  # Index déjà présent

    print("[startup] Index RAG absent — reconstruction depuis la base de données...")
    try:
        from tools.database import lire_articles_actifs
        from tools.rag import indexer_articles
        articles = lire_articles_actifs()
        if not articles:
            print("[startup] Aucun article en base, index RAG non reconstruit.")
            return
        print(f"[startup] {len(articles)} articles récupérés depuis PostgreSQL, indexation...")
        nb = indexer_articles(articles)
        print(f"[startup] Index RAG reconstruit : {nb} chunks indexés.")
    except Exception as e:
        print(f"[startup] Reconstruction RAG échouée (non bloquant) : {e}")


if __name__ == "__main__":
    import sys
    try:
        run()
        _rebuild_rag_if_needed()
    except Exception as e:
        print(f"[startup] ERREUR FATALE : {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
