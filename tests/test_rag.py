"""
Test du module RAG v2 — recherche sémantique, filtres et score hybride.
Utilisation : python test_rag.py
"""
import time
import logging
from tools.rag import rechercher_articles, taille_index

logging.basicConfig(level=logging.WARNING)

REQUETES = [
    # (requete, categorie_attendue, filtre_categorie, filtre_pertinence_min)
    ("GPU et performances IA",                    "IA",              None,   None),
    ("Sécurité des agents LLM en production",     "Cybersécurité",   None,   None),
    ("Nouveaux services AWS et Azure",            "Cloud",           None,   None),
    ("Pipelines CI/CD et automatisation",         "DevOps ou Cybersécurité", None, None),
    ("Bases de données vectorielles pour le RAG", "Données",         None,   None),
    ("Startups européennes qui lèvent des fonds", "IA",              None,   None),
    ("Protéger son entreprise contre les hackers","Cybersécurité",   None,   None),
    ("Réduire sa facture cloud",                  "Cloud",           None,   None),
    ("Déployer des apps sans gérer des serveurs", "DevOps ou Cloud", None,   None),
    ("Traçabilité et conformité RGPD des données","Données",         None,   None),
    ("Impact de l'IA sur la cybersécurité",       "IA ou Cybersécurité", None, None),
    ("Infrastructure pour entraîner des modèles", "IA ou Cloud",     None,   None),
    ("Législation européenne tech",               "IA ou Cybersécurité", None, None),
    # Requêtes avec filtres métadonnées
    ("Kubernetes et infrastructure",              "Infrastructure",  "Infrastructure", None),
    ("Dernières failles critiques",               "Cybersécurité",   "Cybersécurité",  8),
]

if __name__ == "__main__":
    print("=" * 70)
    print(f"TEST RAG v2 — {taille_index()} articles dans l'index")
    print("=" * 70)

    if taille_index() == 0:
        print("Index vide — lancez d'abord : python seed.py")
        exit(1)

    ok = 0
    debut = time.time()

    for requete, categorie_attendue, filtre_cat, filtre_pert in REQUETES:
        resultats = rechercher_articles(
            requete,
            n=2,
            categorie=filtre_cat,
            pertinence_min=filtre_pert,
        )
        top = resultats[0] if resultats else None
        cat = top["categorie"] if top else "—"
        titre = top["titre"][:52] if top else "—"

        score_s = top["score_similarite"] if top else 0
        score_f = top["score_fraicheur"] if top else 0
        score_h = top["score_final"] if top else 0

        attendu_ok = any(c.strip() in cat for c in categorie_attendue.split("ou"))
        if attendu_ok:
            ok += 1
        symbole = "✓" if attendu_ok else "~"

        filtre_info = f" [filtre: {filtre_cat or ''}{f' pert>={filtre_pert}' if filtre_pert else ''}]".rstrip()
        print(f"\n  {symbole} {requete}{filtre_info}")
        print(f"       → {titre}... ({cat})")
        print(f"         sim={score_s:.2f}  fraîcheur={score_f:.2f}  final={score_h:.2f}")

    duree = time.time() - debut
    print(f"\n{'='*70}")
    print(f"Score    : {ok}/{len(REQUETES)} requêtes correctes en top 1")
    print(f"Durée    : {duree:.2f}s pour {len(REQUETES)} recherches")
    print("="*70)
