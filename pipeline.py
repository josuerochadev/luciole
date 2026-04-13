"""
Pipeline de veille technologique :
RSS → filtrage thématique → enrichissement LLM → sauvegarde + indexation RAG.

Utilisation : python pipeline.py
"""
import logging
import time

from tools.search import recuperer_articles_rss, filtrer_par_theme
from tools.database import sauvegarder_articles, article_deja_traite
from llm import resumer_article
from config import PERTINENCE_MIN

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def run():
    """Exécute le pipeline complet de veille technologique."""

    # --- Étape 1 — Collecte RSS ---
    print("\n[1/4] Collecte RSS...")
    articles = recuperer_articles_rss()
    print(f"      {len(articles)} articles récupérés.")

    # --- Étape 2 — Filtrage thématique ---
    print("[2/4] Filtrage thématique...")
    filtres = filtrer_par_theme(articles)
    print(f"      {len(filtres)} articles retenus.")

    # --- Étape 3 — Enrichissement LLM (résumé + catégorie + pertinence) ---
    print(f"[3/4] Enrichissement LLM (seuil pertinence >= {PERTINENCE_MIN})...")

    nouveaux = [a for a in filtres if not article_deja_traite(a["lien"])]
    print(f"      {len(nouveaux)} nouveaux articles à enrichir (doublons exclus).")

    enrichis = []
    for i, article in enumerate(nouveaux, 1):
        titre = article.get("titre", "")
        contenu = article.get("resume_brut", "")
        try:
            analyse = resumer_article(titre, contenu)
            pertinence = int(analyse.get("pertinence", 0))

            if pertinence < PERTINENCE_MIN:
                print(f"      [{i}/{len(nouveaux)}] Ignoré (pertinence {pertinence}) : {titre[:50]}")
                continue

            article.update({
                "resume":     analyse.get("resume", contenu[:300]),
                "categorie":  analyse.get("categorie", "Autre"),
                "pertinence": pertinence,
                "action":     analyse.get("action", "lire"),
            })
            enrichis.append(article)
            print(f"      [{i}/{len(nouveaux)}] ✓ [{pertinence}/10] {analyse.get('categorie','?')} — {titre[:50]}")

        except Exception as e:
            logging.warning(f"Enrichissement échoué pour '{titre}' : {e}")
            article.setdefault("categorie", "Autre")
            article.setdefault("pertinence", 5)
            enrichis.append(article)

        if i % 10 == 0:
            time.sleep(1)

    print(f"      {len(enrichis)} articles enrichis et pertinents.")

    # --- Étape 4 — Sauvegarde + indexation RAG ---
    print("[4/4] Sauvegarde et indexation RAG...")
    nb = sauvegarder_articles(enrichis)
    print(f"      {nb} articles sauvegardés et indexés.")

    print(f"\n✓ Pipeline terminé — {nb} nouveaux articles dans la base.\n")
    return nb


if __name__ == "__main__":
    run()
