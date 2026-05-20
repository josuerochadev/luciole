"""
Enrichissement retroactif des articles "Non classe" via Gemini.
A lancer quand le quota journalier Gemini est disponible.

Usage :
  python enrichir_articles.py              # enrichit tous les articles non classes
  python enrichir_articles.py --limit 500  # enrichit les N premiers seulement
  python enrichir_articles.py --dry-run    # affiche ce qui serait enrichi sans modifier la base
"""
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from db_utils import connect, cursor
from tools.enrichment import enrichir_article
from config import PERTINENCE_MIN

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LLM_WORKERS = 5
BATCH_COMMIT_SIZE = 50  # commit tous les N articles pour eviter de tout perdre


def charger_articles_non_classes(limit: int | None = None) -> list[dict]:
    conn = connect()
    try:
        cur = cursor(conn)
        query = """
            SELECT lien, titre, resume_brut, contenu_complet
            FROM articles
            WHERE categorie = 'Non classe'
            ORDER BY date_ajout DESC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        cur.execute(query)
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def mettre_a_jour_article(lien: str, resume: str, categorie: str, pertinence: int, action: str, conn, cur):
    cur.execute(
        """
        UPDATE articles
        SET resume = %s, categorie = %s, pertinence = %s, action = %s
        WHERE lien = %s
        """,
        (resume, categorie, pertinence, action, lien),
    )


def run(limit: int | None = None, dry_run: bool = False):
    articles = charger_articles_non_classes(limit)
    total = len(articles)
    print(f"\n{total} articles a enrichir.\n")

    if total == 0:
        print("Rien a faire.")
        return

    enrichis = []
    ignores = 0
    erreurs = 0
    done = 0

    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as pool:
        futures = {pool.submit(enrichir_article, a): a for a in articles}
        for future in as_completed(futures):
            done += 1
            original = futures[future]
            titre = original.get("titre", "")[:50]
            try:
                result = future.result()
                if result is None:
                    ignores += 1
                    print(f"  [{done}/{total}] Ignore (pertinence < {PERTINENCE_MIN}) : {titre}")
                else:
                    p = result.get("pertinence", "?")
                    c = result.get("categorie", "?")
                    print(f"  [{done}/{total}] {c} [{p}/10] — {titre}")
                    enrichis.append(result)
            except Exception as e:
                erreurs += 1
                logger.warning(f"Erreur enrichissement '{titre}': {e}")
                print(f"  [{done}/{total}] ERREUR : {titre}")

            # Commit par batch pour ne pas tout perdre
            if not dry_run and len(enrichis) > 0 and len(enrichis) % BATCH_COMMIT_SIZE == 0:
                _sauvegarder_batch(enrichis[-BATCH_COMMIT_SIZE:])
                print(f"  --- batch de {BATCH_COMMIT_SIZE} sauvegarde ---")

    # Sauvegarder le reste
    if not dry_run and enrichis:
        reste = len(enrichis) % BATCH_COMMIT_SIZE
        if reste > 0:
            _sauvegarder_batch(enrichis[-reste:])

    print("\nResultat :")
    print(f"  Enrichis : {len(enrichis)}")
    print(f"  Ignores (pertinence faible) : {ignores}")
    print(f"  Erreurs : {erreurs}")
    if dry_run:
        print("  (dry-run — aucune modification en base)")
    print()


def _sauvegarder_batch(articles: list[dict]):
    conn = connect()
    try:
        cur = cursor(conn)
        for a in articles:
            mettre_a_jour_article(
                a["lien"],
                a.get("resume", ""),
                a.get("categorie", "Autre"),
                int(a.get("pertinence", 0)),
                a.get("action", "lire"),
                conn, cur,
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrichissement retroactif des articles")
    parser.add_argument("--limit", type=int, default=None, help="Nombre max d'articles a enrichir")
    parser.add_argument("--dry-run", action="store_true", help="Afficher sans modifier la base")
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)
