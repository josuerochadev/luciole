"""
Étape 3 — Embeddings + Stockage ChromaDB.
Génère les embeddings avec text-embedding-3-small et les stocke dans ChromaDB
avec métadonnées (source, page).
"""
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chromadb_data")
COLLECTION_NAME = "cnil_docs"
BATCH_SIZE = 100  # OpenAI accepte jusqu'à 2048 inputs par appel


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante dans .env")
    return OpenAI(api_key=api_key)


def get_collection() -> chromadb.Collection:
    """Retourne la collection ChromaDB (la crée si elle n'existe pas)."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def indexer_chunks(chunks: list[dict]) -> int:
    """
    Génère les embeddings et stocke les chunks dans ChromaDB.

    Args:
        chunks: Liste de dicts avec texte, source, page, chunk_id.

    Returns:
        Nombre de chunks indexés.
    """
    if not chunks:
        return 0

    openai_client = _get_client()
    collection = get_collection()

    total = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        textes = [c["texte"] for c in batch]

        # Générer les embeddings en batch
        response = openai_client.embeddings.create(
            input=textes,
            model=EMBEDDING_MODEL,
        )
        embeddings = [item.embedding for item in response.data]

        # Stocker dans ChromaDB
        collection.upsert(
            ids=[c["chunk_id"] for c in batch],
            embeddings=embeddings,
            documents=textes,
            metadatas=[{"source": c["source"], "page": c["page"]} for c in batch],
        )
        total += len(batch)
        print(f"  Indexé {total}/{len(chunks)} chunks...")

    return total


def rechercher(query: str, n: int = 3) -> list[dict]:
    """
    Recherche les chunks les plus similaires à la requête.

    Args:
        query: Question en langage naturel.
        n:     Nombre de résultats.

    Returns:
        Liste de dicts avec: texte, source, page, score.
    """
    openai_client = _get_client()
    collection = get_collection()

    response = openai_client.embeddings.create(
        input=[query],
        model=EMBEDDING_MODEL,
    )
    query_embedding = response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
    )

    resultats = []
    for i in range(len(results["ids"][0])):
        resultats.append({
            "texte": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "page": results["metadatas"][0][i]["page"],
            "score": round(1 - results["distances"][0][i], 3),
        })

    return resultats


if __name__ == "__main__":
    from ingest import ingerer_dossier
    from chunk import decouper_en_chunks

    dossier = os.path.join(os.path.dirname(__file__), "..", "cnil")
    print("[1/3] Ingestion...")
    pages = ingerer_dossier(dossier)

    print(f"\n[2/3] Chunking...")
    chunks = decouper_en_chunks(pages)
    print(f"  {len(chunks)} chunks créés.")

    print(f"\n[3/3] Indexation ChromaDB...")
    nb = indexer_chunks(chunks)
    print(f"\n✓ {nb} chunks indexés dans ChromaDB.")
