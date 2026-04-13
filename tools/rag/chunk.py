"""
Étape 2 — Chunking.
Découpe chaque page en morceaux de ~500 mots avec chevauchement de 50 mots.
"""


def decouper_en_chunks(
    pages: list[dict],
    taille: int = 500,
    chevauchement: int = 50,
) -> list[dict]:
    """
    Découpe les pages en chunks de taille fixe (en mots) avec chevauchement.

    Args:
        pages:          Liste de dicts avec texte, source, page.
        taille:         Nombre de mots par chunk.
        chevauchement:  Nombre de mots de chevauchement entre chunks.

    Returns:
        Liste de dicts avec: texte, source, page, chunk_id.
    """
    chunks = []
    chunk_id = 0

    for page in pages:
        mots = page["texte"].split()

        if len(mots) <= taille:
            chunks.append({
                "texte": page["texte"],
                "source": page["source"],
                "page": page["page"],
                "chunk_id": f"chunk_{chunk_id}",
            })
            chunk_id += 1
            continue

        debut = 0
        while debut < len(mots):
            fin = debut + taille
            texte_chunk = " ".join(mots[debut:fin])

            chunks.append({
                "texte": texte_chunk,
                "source": page["source"],
                "page": page["page"],
                "chunk_id": f"chunk_{chunk_id}",
            })
            chunk_id += 1

            debut += taille - chevauchement

    return chunks


if __name__ == "__main__":
    from ingest import ingerer_dossier
    import os

    dossier = os.path.join(os.path.dirname(__file__), "..", "cnil")
    pages = ingerer_dossier(dossier)
    chunks = decouper_en_chunks(pages)

    print(f"\n{len(pages)} pages → {len(chunks)} chunks")
    if chunks:
        exemple = chunks[0]
        nb_mots = len(exemple["texte"].split())
        print(f"Exemple chunk_0 : {nb_mots} mots, source={exemple['source']}, page={exemple['page']}")
