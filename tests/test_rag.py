"""
Test du module RAG v3 — chunking, HyDE, cache, seuil de score.
Utilisation : python test_rag.py
"""
import time
import logging
from tools.rag import rechercher_articles, taille_index, _chunker, _tokenize, SCORE_MINIMUM

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


def test_chunker():
    """Test unitaire du chunking."""
    print("\n--- Test chunking ---")
    texte_court = "Ceci est un texte court."
    chunks = _chunker(texte_court)
    assert len(chunks) == 1, f"Texte court devrait donner 1 chunk, got {len(chunks)}"
    print(f"  ✓ Texte court → {len(chunks)} chunk")

    texte_long = " ".join([f"mot{i}" for i in range(1200)])
    chunks = _chunker(texte_long, chunk_size=500, overlap=80)
    assert len(chunks) >= 3, f"1200 mots / 500 devrait donner >=3 chunks, got {len(chunks)}"
    # Vérifier l'overlap : les chunks consécutifs partagent des mots
    mots_c1 = set(chunks[0].split()[-80:])
    mots_c2 = set(chunks[1].split()[:80])
    overlap = mots_c1 & mots_c2
    assert len(overlap) > 0, "Les chunks doivent avoir un overlap"
    print(f"  ✓ 1200 mots → {len(chunks)} chunks (overlap OK: {len(overlap)} mots)")


def test_tokenize():
    """Test unitaire de la tokenisation BM25."""
    print("\n--- Test tokenisation BM25 ---")
    tokens = _tokenize("Les nouvelles failles de sécurité dans Kubernetes 2024")
    assert "les" not in tokens, "Stop word 'les' ne devrait pas être dans les tokens"
    assert "de" not in tokens, "Stop word 'de' ne devrait pas être dans les tokens"
    assert "failles" in tokens, "'failles' devrait être dans les tokens"
    assert "kubernetes" in tokens, "'kubernetes' devrait être dans les tokens"
    assert "2024" in tokens, "'2024' devrait être dans les tokens"
    print(f"  ✓ Tokenisation: {tokens}")

    tokens_en = _tokenize("The latest AI breakthroughs in machine learning")
    assert "the" not in tokens_en
    assert "in" not in tokens_en
    assert "latest" in tokens_en
    assert "machine" in tokens_en
    print(f"  ✓ Tokenisation EN: {tokens_en}")


def test_score_minimum():
    """Vérifie que le seuil de score est configuré."""
    print("\n--- Test seuil de score ---")
    assert SCORE_MINIMUM > 0, "SCORE_MINIMUM doit être > 0"
    assert SCORE_MINIMUM < 1, "SCORE_MINIMUM doit être < 1"
    print(f"  ✓ SCORE_MINIMUM = {SCORE_MINIMUM}")


def test_recherche_rag():
    """Test d'intégration de la recherche RAG."""
    print(f"\n{'='*70}")
    print(f"TEST RAG v3 — {taille_index()} entrées dans l'index")
    print("=" * 70)

    if taille_index() == 0:
        print("Index vide — lancez d'abord : python seed.py puis réindexez")
        return 0, len(REQUETES)

    ok = 0
    debut = time.time()

    for requete, categorie_attendue, filtre_cat, filtre_pert in REQUETES:
        resultats = rechercher_articles(
            requete,
            n=2,
            categorie=filtre_cat,
            pertinence_min=filtre_pert,
            hyde=False,  # Désactiver HyDE pour les tests (économise les appels API)
        )
        top = resultats[0] if resultats else None
        cat = top["categorie"] if top else "—"
        titre = top["titre"][:52] if top else "—"

        score_s = top["score_similarite"] if top else 0
        score_f = top["score_fraicheur"] if top else 0
        score_h = top["score_final"] if top else 0
        chunks = top.get("chunks_utilises", 1) if top else 0
        extrait_len = len(top.get("resume_extrait", "")) if top else 0

        attendu_ok = any(c.strip() in cat for c in categorie_attendue.split("ou"))
        if attendu_ok:
            ok += 1
        symbole = "✓" if attendu_ok else "~"

        filtre_info = f" [filtre: {filtre_cat or ''}{f' pert>={filtre_pert}' if filtre_pert else ''}]".rstrip()
        print(f"\n  {symbole} {requete}{filtre_info}")
        print(f"       → {titre}... ({cat})")
        print(f"         sim={score_s:.2f}  fraîcheur={score_f:.2f}  final={score_h:.2f}  chunks={chunks}  contexte={extrait_len}c")

    duree = time.time() - debut
    print(f"\n{'='*70}")
    print(f"Score    : {ok}/{len(REQUETES)} requêtes correctes en top 1")
    print(f"Durée    : {duree:.2f}s pour {len(REQUETES)} recherches")
    print(f"Seuil    : score_final >= {SCORE_MINIMUM}")
    print("=" * 70)
    return ok, len(REQUETES)


if __name__ == "__main__":
    test_chunker()
    test_tokenize()
    test_score_minimum()
    test_recherche_rag()
