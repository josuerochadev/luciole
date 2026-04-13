"""
Étape 4 — Interrogation du pipeline RAG.
Recherche les chunks pertinents et génère une réponse contextuelle via LLM.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
from vectorstore import rechercher

load_dotenv()

MODEL = "gpt-4o-mini"


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante dans .env")
    return OpenAI(api_key=api_key)


def rag_query(question: str, n_chunks: int = 3) -> dict:
    """
    Pipeline RAG complet : recherche sémantique + génération de réponse.

    Args:
        question: Question en langage naturel.
        n_chunks: Nombre de chunks à récupérer.

    Returns:
        Dict avec: reponse, sources, chunks_utilises.
    """
    # 1. Recherche des chunks pertinents
    chunks = rechercher(question, n=n_chunks)

    if not chunks:
        return {
            "reponse": "Aucun document pertinent trouvé dans le corpus.",
            "sources": [],
            "chunks_utilises": [],
        }

    # 2. Construction du contexte
    contexte = ""
    sources = []
    for i, chunk in enumerate(chunks, 1):
        contexte += f"\n--- Extrait {i} (source: {chunk['source']}, page {chunk['page']}, score: {chunk['score']}) ---\n"
        contexte += chunk["texte"] + "\n"
        source_info = f"{chunk['source']} (p.{chunk['page']})"
        if source_info not in sources:
            sources.append(source_info)

    # 3. Génération de la réponse
    system_prompt = (
        "Tu es un assistant spécialisé en protection des données personnelles et RGPD. "
        "Réponds UNIQUEMENT à partir du contexte fourni ci-dessous. "
        "Si la réponse ne se trouve pas dans le contexte, dis-le clairement. "
        "Cite toujours les sources (nom du document et numéro de page). "
        "Réponds en français."
    )

    user_prompt = f"Contexte :\n{contexte}\n\nQuestion : {question}"

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    reponse = response.choices[0].message.content.strip()

    return {
        "reponse": reponse,
        "sources": sources,
        "chunks_utilises": chunks,
    }


if __name__ == "__main__":
    # --- Étape 5 : Tests ---
    questions_test = [
        # Question 1 — dans le corpus (RGPD)
        "Quels sont les droits des personnes concernées selon le RGPD ?",
        # Question 2 — dans le corpus (sécurité)
        "Quelles sont les recommandations de la CNIL en matière de sécurité des données personnelles ?",
        # Question hors corpus
        "Quel est le cours actuel de l'action Apple en bourse ?",
    ]

    print("=" * 70)
    print("TESTS DU PIPELINE RAG — CORPUS CNIL")
    print("=" * 70)

    resultats_test = []
    for i, question in enumerate(questions_test, 1):
        print(f"\n{'─' * 70}")
        print(f"Question {i} : {question}")
        print("─" * 70)

        resultat = rag_query(question)

        print(f"\nRéponse :\n{resultat['reponse']}")
        print(f"\nSources : {', '.join(resultat['sources']) if resultat['sources'] else 'Aucune'}")
        print(f"Scores  : {[c['score'] for c in resultat['chunks_utilises']]}")

        resultats_test.append({
            "question": question,
            "reponse_pertinente": "?" ,
            "source_citee": bool(resultat["sources"]),
            "hors_corpus_gere": i == 3,
        })

    # Tableau récapitulatif
    print(f"\n{'=' * 70}")
    print("TABLEAU RÉCAPITULATIF")
    print(f"{'=' * 70}")
    print(f"{'Question':<60} {'Pertinente?':<14} {'Source?':<10} {'Hors corpus?'}")
    print("─" * 95)
    for r in resultats_test:
        q = r["question"][:57] + "..." if len(r["question"]) > 57 else r["question"]
        print(f"{q:<60} {'à vérifier':<14} {'oui' if r['source_citee'] else 'non':<10} {'oui' if r['hors_corpus_gere'] else 'non'}")
