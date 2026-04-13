"""
Exercice 2 — Tests de appeler_llm_json()
Valide le comportement sur 4 cas limites du projet de veille technologique.

Utilisation : python test_llm_json.py
"""
import logging
import json
from llm import appeler_llm_json, SCHEMA_VEILLE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

SEPARATEUR = "-" * 60


def afficher_resultat(nom: str, message: str, resultat: dict) -> None:
    print(f"\n{SEPARATEUR}")
    print(f"TEST : {nom}")
    print(f"INPUT : {message[:80]}{'...' if len(message) > 80 else ''}")
    print(f"OUTPUT :\n{json.dumps(resultat, ensure_ascii=False, indent=2)}")
    if resultat.get("_parsing_error"):
        print("⚠ ATTENTION : fallback activé, la réponse n'était pas du JSON valide.")


# ---------------------------------------------------------------------------
# Test 1 — Message ambigu
# ---------------------------------------------------------------------------
def test_message_ambigu():
    """
    'Salut, ça va ?' n'est pas un article technologique.
    Attendu : pertinence faible (1-3), categorie=Hors-sujet, action=ignorer.
    Observation : le LLM doit gérer proprement l'absence de contenu métier.
    """
    message = "Salut, ça va ?"
    resultat = appeler_llm_json(message)
    afficher_resultat("Message ambigu", message, resultat)

    assert "pertinence" in resultat, "Clé 'pertinence' manquante"
    assert "categorie" in resultat, "Clé 'categorie' manquante"
    assert "resume" in resultat, "Clé 'resume' manquante"
    assert "action" in resultat, "Clé 'action' manquante"
    assert isinstance(resultat["pertinence"], int), "'pertinence' doit être un entier"
    print("✓ Structure JSON valide")
    print(f"  → Pertinence retournée : {resultat['pertinence']} (attendu : faible)")
    print(f"  → Catégorie : {resultat['categorie']}")


# ---------------------------------------------------------------------------
# Test 2 — Message long (email ~500 mots)
# ---------------------------------------------------------------------------
def test_message_long():
    """
    Email professionnel long sur un sujet technologique (migration cloud AWS).
    Attendu : résumé condensé, pertinence élevée (7-10), categorie=Cloud.
    Observation : le LLM doit résumer sans dépasser le schéma.
    """
    message = """
Objet : Compte-rendu de la réunion de migration infrastructure — Phase 2

Bonjour à toutes et tous,

Suite à notre réunion du 8 avril, je vous adresse ce compte-rendu détaillé concernant
la migration de notre infrastructure on-premise vers AWS qui entrera en phase 2 dès
le mois prochain.

Points abordés :

1. Architecture cible
Notre équipe a validé une architecture multi-comptes AWS avec trois environnements
distincts : développement, staging et production. Chaque environnement sera isolé
dans un compte AWS dédié, géré via AWS Organizations. Le transit entre comptes
passera par AWS Transit Gateway pour simplifier le peering VPC.

2. Outils de migration
Nous utiliserons AWS Migration Hub pour le suivi centralisé. Les bases de données
seront migrées via AWS DMS (Database Migration Service) avec une phase de réplication
continue avant bascule. Les serveurs applicatifs passeront par AWS Application
Migration Service (anciennement CloudEndure).

3. Sécurité et conformité
Un audit IAM complet a été commandé. Toutes les ressources devront respecter le
principe du moindre privilège. Les secrets seront stockés dans AWS Secrets Manager.
Un contrôle de conformité automatisé via AWS Config et Security Hub sera mis en place
dès le début de la phase 2.

4. Calendrier
- Semaine 1-2 : déploiement des comptes AWS et des rôles IAM de base
- Semaine 3-4 : migration des bases de données non critiques
- Semaine 5-6 : migration des applications tier 2
- Semaine 7-8 : tests de charge et bascule du tier 1
- Semaine 9 : coupure de l'infrastructure on-premise et décommissionnement

5. Budget
Le budget validé est de 85 000€ pour la phase 2, dont 40% dédié aux licences et
services AWS, 35% aux ressources humaines internes et externes, et 25% aux tests
et à la formation des équipes.

6. Risques identifiés
Le principal risque est la latence réseau lors de la réplication des bases Oracle.
Nous avons prévu une fenêtre de maintenance de 4h pour la bascule finale.
Un plan de rollback complet a été documenté.

N'hésitez pas à revenir vers moi pour toute question.

Cordialement,
Thomas Renard, Responsable Infrastructure
""".strip()

    resultat = appeler_llm_json(message)
    afficher_resultat("Message long (email ~500 mots)", message, resultat)

    assert "resume" in resultat
    assert len(resultat["resume"]) > 20, "Le résumé semble trop court"
    print("✓ Structure JSON valide")
    print(f"  → Longueur du résumé : {len(resultat['resume'])} caractères")
    print(f"  → Pertinence : {resultat['pertinence']}, Catégorie : {resultat['categorie']}")


# ---------------------------------------------------------------------------
# Test 3 — Message hors sujet
# ---------------------------------------------------------------------------
def test_hors_sujet():
    """
    Question de géographie sans lien avec la tech.
    Attendu : pertinence très faible (1-2), categorie=Hors-sujet, action=ignorer.
    Observation : le LLM ne doit pas inventer un lien technologique.
    """
    message = "Quelle est la capitale de la France ?"
    resultat = appeler_llm_json(message)
    afficher_resultat("Message hors sujet", message, resultat)

    assert "pertinence" in resultat
    print("✓ Structure JSON valide")
    print(f"  → Pertinence : {resultat['pertinence']} (attendu : très faible)")
    print(f"  → Action : {resultat['action']} (attendu : ignorer)")


# ---------------------------------------------------------------------------
# Test 4 — Message agressif
# ---------------------------------------------------------------------------
def test_message_agressif():
    """
    Plainte agressive sans contenu technologique.
    Attendu : réponse structurée sans reproduire l'agressivité, pertinence faible.
    Observation : le LLM doit rester factuel et ne pas être déstabilisé.
    """
    message = "Votre service est NUL, ça fait 3 fois que mon rapport ne part pas !"
    resultat = appeler_llm_json(message)
    afficher_resultat("Message agressif", message, resultat)

    assert "resume" in resultat
    assert "pertinence" in resultat
    print("✓ Structure JSON valide")
    print(f"  → Le résumé est-il neutre ? : {resultat['resume']}")
    print(f"  → Catégorie assignée : {resultat['categorie']}")


# ---------------------------------------------------------------------------
# Lancement de tous les tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("EXERCICE 2 — Tests de appeler_llm_json()")
    print(f"Schéma utilisé : {list(SCHEMA_VEILLE.keys())}")
    print("=" * 60)

    tests = [
        ("Message ambigu",   test_message_ambigu),
        ("Message long",     test_message_long),
        ("Hors sujet",       test_hors_sujet),
        ("Message agressif", test_message_agressif),
    ]

    resultats = []
    for nom, fn in tests:
        try:
            fn()
            resultats.append((nom, "PASS"))
        except AssertionError as e:
            resultats.append((nom, f"FAIL — {e}"))
        except Exception as e:
            resultats.append((nom, f"ERREUR — {e}"))

    print(f"\n{'=' * 60}")
    print("RÉSUMÉ DES TESTS")
    print(f"{'=' * 60}")
    for nom, statut in resultats:
        symbole = "✓" if statut == "PASS" else "✗"
        print(f"  {symbole} {nom:<25} {statut}")
    print()
