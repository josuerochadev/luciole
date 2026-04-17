"""
Pipeline de veille technologique :
RSS → filtrage thématique → enrichissement LLM → sauvegarde + indexation RAG → digest email.

Utilisation :
  python pipeline.py              # pipeline complet avec envoi email (one-shot)
  python pipeline.py --dry-run    # pipeline complet, email généré mais non envoyé
  python pipeline.py --no-email   # pipeline sans étape email
  python pipeline.py --schedule   # lance le scheduler (exécution quotidienne)
"""
import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from difflib import SequenceMatcher

from tools.search import recuperer_articles_rss, filtrer_par_theme
from tools.scraper import scraper_articles_batch
from tools.database import sauvegarder_articles, article_deja_traite
from tools.email import selectionner_articles, envoyer_rapport
from llm import resumer_article
from config import PERTINENCE_MIN

TITRE_SIMILARITY_THRESHOLD = 0.85  # seuil de similarité pour considérer un doublon


def _dedoublonner_par_titre(articles: list[dict]) -> list[dict]:
    """
    Supprime les articles dont le titre est quasi-identique (même sujet,
    syndiqué sur plusieurs flux). Garde le premier rencontré.
    """
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

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run(dry_run: bool = False, no_email: bool = False) -> dict:
    """
    Exécute le pipeline complet de veille technologique.

    Args:
        dry_run:  Si True, génère le digest sans envoyer d'email.
        no_email: Si True, skip entièrement l'étape email.

    Returns:
        Dict avec nb_articles_sauvegardes et resultat_email.
    """
    nb_etapes = 4 if no_email else 5

    # --- Étape 1 — Collecte RSS ---
    print(f"\n[1/{nb_etapes}] Collecte RSS...")
    articles = recuperer_articles_rss()
    print(f"      {len(articles)} articles récupérés.")

    # --- Étape 2 — Filtrage thématique ---
    print(f"[2/{nb_etapes}] Filtrage thématique...")
    filtres = filtrer_par_theme(articles)
    print(f"      {len(filtres)} articles retenus.")

    # --- Étape 3a — Scraping du contenu complet ---
    nouveaux = [a for a in filtres if not article_deja_traite(a["lien"])]
    avant_dedup = len(nouveaux)
    nouveaux = _dedoublonner_par_titre(nouveaux)
    print(f"      {len(nouveaux)} nouveaux articles ({avant_dedup - len(nouveaux)} doublons titre supprimés).")

    nb_etapes_total = nb_etapes + 1 if not no_email else nb_etapes + 1
    print(f"[3/{nb_etapes_total}] Scraping du contenu complet...")
    nouveaux = scraper_articles_batch(nouveaux)
    nb_scrapes = sum(1 for a in nouveaux if a.get("contenu_complet"))
    print(f"      {nb_scrapes}/{len(nouveaux)} articles scrapés avec succès.")

    # --- Étape 4 — Enrichissement LLM parallèle (résumé + catégorie + pertinence) ---
    print(f"[4/{nb_etapes_total}] Enrichissement LLM (seuil pertinence >= {PERTINENCE_MIN}, 5 threads)...")

    LLM_WORKERS = 5  # threads parallèles pour l'API OpenAI

    def _enrichir_un(article: dict) -> dict | None:
        """Enrichit un article via le LLM. Retourne l'article enrichi ou None."""
        titre = article.get("titre", "")
        contenu = article.get("contenu_complet", article.get("resume_brut", ""))
        try:
            analyse = resumer_article(titre, contenu)
            pertinence = int(analyse.get("pertinence", 0))
            if pertinence < PERTINENCE_MIN:
                return None
            article.update({
                "resume":     analyse.get("resume", contenu[:300]),
                "categorie":  analyse.get("categorie", "Autre"),
                "pertinence": pertinence,
                "action":     analyse.get("action", "lire"),
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
        futures = {pool.submit(_enrichir_un, a): a for a in nouveaux}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            titre = futures[future].get("titre", "")[:50]
            if result is None:
                print(f"      [{done}/{len(nouveaux)}] Ignoré (pertinence faible) : {titre}")
            else:
                p = result.get("pertinence", "?")
                c = result.get("categorie", "?")
                print(f"      [{done}/{len(nouveaux)}] ✓ [{p}/10] {c} — {titre}")
                enrichis.append(result)

    print(f"      {len(enrichis)} articles enrichis et pertinents.")

    # --- Étape 5 — Sauvegarde + indexation RAG ---
    print(f"[5/{nb_etapes_total}] Sauvegarde et indexation RAG...")
    nb = sauvegarder_articles(enrichis)
    print(f"      {nb} articles sauvegardés et indexés.")

    # --- Étape 6 — Envoi du digest email ---
    resultat_email = None
    if not no_email:
        print(f"[6/{nb_etapes_total}] Envoi du digest email{' (dry-run)' if dry_run else ''}...")
        articles_digest = selectionner_articles()

        if not articles_digest:
            print("      Aucun article pertinent pour le digest.")
            resultat_email = {"ok": False, "nb_articles": 0, "message": "Aucun article pertinent."}
        else:
            resultat_email = envoyer_rapport(dry_run=dry_run)
            if resultat_email["ok"]:
                print(f"      ✓ Digest {'généré' if dry_run else 'envoyé'} — {resultat_email['nb_articles']} articles.")
            else:
                print(f"      ✗ Échec : {resultat_email['message']}")
                logger.error(f"[Pipeline] Envoi digest échoué : {resultat_email['message']}")

    mode = " (dry-run)" if dry_run else " (sans email)" if no_email else ""
    print(f"\n✓ Pipeline terminé{mode} — {nb} nouveaux articles dans la base.\n")

    return {"nb_articles_sauvegardes": nb, "resultat_email": resultat_email}


def start_scheduler(dry_run: bool = False, no_email: bool = False) -> None:
    """Lance le scheduler APScheduler qui exécute le pipeline quotidiennement."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    veille_heure = os.environ.get("VEILLE_HEURE", "08:00")
    heure, minute = veille_heure.split(":")

    def job():
        horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.warning(f"[Scheduler] Exécution planifiée démarrée à {horodatage}")
        print(f"\n{'='*60}")
        print(f"[Scheduler] Exécution planifiée — {horodatage}")
        print(f"{'='*60}")
        try:
            result = run(dry_run=dry_run, no_email=no_email)
            logger.warning(f"[Scheduler] Terminé — {result['nb_articles_sauvegardes']} articles sauvegardés")
        except Exception as e:
            logger.error(f"[Scheduler] Échec de l'exécution planifiée : {e}")

    scheduler = BlockingScheduler()
    scheduler.add_job(job, CronTrigger(hour=int(heure), minute=int(minute)))

    print(f"🕐 Scheduler démarré — pipeline planifié chaque jour à {veille_heure}")
    print(f"   (configurable via VEILLE_HEURE, Ctrl+C pour arrêter)\n")
    logger.warning(f"[Scheduler] Démarré — exécution quotidienne à {veille_heure}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹ Scheduler arrêté.")
        logger.warning("[Scheduler] Arrêté par l'utilisateur")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de veille technologique")
    parser.add_argument("--dry-run", action="store_true", help="Générer le digest sans envoyer d'email")
    parser.add_argument("--no-email", action="store_true", help="Exécuter le pipeline sans étape email")
    parser.add_argument("--schedule", action="store_true", help="Lancer le scheduler (exécution quotidienne)")
    args = parser.parse_args()

    if args.schedule:
        start_scheduler(dry_run=args.dry_run, no_email=args.no_email)
    else:
        run(dry_run=args.dry_run, no_email=args.no_email)
