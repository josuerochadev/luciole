"""
Exercice 5 — Tester l'agent avec des requêtes pièges adaptées au projet de veille technologique.
Utilisation : python test_agent_debug.py
"""
import logging
from main import agent_react

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

SEPARATEUR = "=" * 60

REQUETES_PIEGES = [
    {
        "nom":     "Faute de frappe",
        "requete": "Tendence sur l IA en 2026",
        "attendu": "search_web — doit inférer 'tendances IA 2026' malgré les fautes et retourner des articles pertinents",
    },
    {
        "nom":     "2 intentions mélangées",
        "requete": "Montre les articles Cloud ET envoie le rapport par email",
        "attendu": "Choisit search_web pour la partie Cloud, reconnaît que l'envoi email n'est pas gérable en une seule étape",
    },
    {
        "nom":     "Données inexistantes",
        "requete": "Quel est le score de pertinence de l'article sur NVIDIA ?",
        "attendu": "query_db échoue (colonne absente), le LLM doit reconnaître l'absence sans inventer de score",
    },
    {
        "nom":     "Requête très longue (300+ mots)",
        "requete": (
            "Bonjour, je travaille dans le département IT d'une grande entreprise de services numériques. "
            "Nous sommes en train de revoir notre stratégie de veille technologique pour l'année 2026. "
            "Dans ce cadre, nous cherchons à mieux comprendre les tendances actuelles en matière "
            "d'intelligence artificielle, notamment en ce qui concerne les grands modèles de langage, "
            "leur adoption en entreprise, les coûts d'infrastructure associés, les enjeux de gouvernance "
            "et de conformité réglementaire, ainsi que les meilleures pratiques de déploiement. "
            "Nous nous intéressons également aux évolutions du marché des puces GPU, aux nouvelles "
            "architectures proposées par NVIDIA et AMD, et à leur impact sur les performances des "
            "systèmes d'inférence. Par ailleurs, nous souhaitons surveiller les actualités "
            "en cybersécurité liées à l'IA, notamment les risques de prompt injection, "
            "de fuite de données et d'hallucinations dans les systèmes critiques. "
            "Pourriez-vous nous fournir une synthèse des informations disponibles sur ces sujets ?"
        ),
        "attendu": "search_web, réponse synthétique sans timeout malgré le contexte long",
    },
]


def executer_test(cas: dict) -> dict:
    """Lance un test piège et retourne le résultat sous forme de dict."""
    print(f"\n{'-'*60}")
    print(f"TEST : {cas['nom']}")
    print(f"REQUÊTE : {cas['requete'][:80]}{'...' if len(cas['requete']) > 80 else ''}")
    print(f"ATTENDU : {cas['attendu']}")
    print()

    try:
        reponse = agent_react(cas["requete"])
        return {"nom": cas["nom"], "statut": "OK", "reponse": reponse}
    except Exception as e:
        print(f"ERREUR non gérée : {e}")
        return {"nom": cas["nom"], "statut": "ERREUR", "reponse": str(e)}


if __name__ == "__main__":
    print(SEPARATEUR)
    print("EXERCICE 5 — Requêtes pièges sur l'agent de veille technologique")
    print(SEPARATEUR)

    resultats = [executer_test(cas) for cas in REQUETES_PIEGES]

    print(f"\n{SEPARATEUR}")
    print("RÉSUMÉ")
    print(SEPARATEUR)
    for r in resultats:
        symbole = "✓" if r["statut"] == "OK" else "✗"
        print(f"  {symbole} {r['nom']:<35} {r['statut']}")
