"""
Étape 3 de l'exercice Langfuse : générer 10 requêtes variées
pour alimenter les traces dans Langfuse.
"""

from main import agent_react

REQUETES = [
    # --- Simples (reponse_directe) ---
    "Bonjour, qui es-tu ?",
    "Quel est ton rôle ?",

    # --- Base de données (query_db) ---
    "Combien de clients avons-nous ?",
    "Liste les clients Premium",
    "Quel est le ticket moyen par client ?",

    # --- Recherche web (search_web) ---
    "Briefing matinal : 3 actus IA",
    "Tendances cybersécurité 2026",
    "Quelles sont les dernières nouveautés cloud ?",

    # --- RAG / archives (search_articles) ---
    "Retrouve les articles archivés sur Kubernetes",
    "Résume ce qu'on a dans nos archives sur le machine learning",
]

if __name__ == "__main__":
    print(f"Lancement de {len(REQUETES)} requêtes pour alimenter Langfuse...\n")

    for i, requete in enumerate(REQUETES, 1):
        print(f"\n{'#'*60}")
        print(f"# Requête {i}/{len(REQUETES)}")
        print(f"{'#'*60}")
        try:
            agent_react(requete)
        except Exception as e:
            print(f"[ERREUR] Requête {i} échouée : {e}")

    print(f"\n{'='*60}")
    print(f"Terminé — {len(REQUETES)} traces envoyées à Langfuse.")
    print("Ouvrez https://cloud.langfuse.com pour les consulter.")
    print(f"{'='*60}")
