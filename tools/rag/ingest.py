"""
Étape 1 — Ingestion et nettoyage des PDF.
Extrait le texte de chaque page avec métadonnées (source, numéro de page).
"""
import os
import re
import pdfplumber


def extraire_pages(chemin_pdf: str) -> list[dict]:
    """
    Extrait le texte de chaque page d'un PDF.

    Args:
        chemin_pdf: Chemin vers le fichier PDF.

    Returns:
        Liste de dicts avec: texte, source, page.
    """
    nom_fichier = os.path.basename(chemin_pdf)
    pages = []

    with pdfplumber.open(chemin_pdf) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            texte = page.extract_text() or ""
            texte = _nettoyer(texte)
            if texte.strip():
                pages.append({
                    "texte": texte,
                    "source": nom_fichier,
                    "page": i,
                })

    return pages


def ingerer_dossier(chemin_dossier: str) -> list[dict]:
    """
    Ingère tous les PDF d'un dossier.

    Returns:
        Liste de toutes les pages extraites avec métadonnées.
    """
    toutes_pages = []

    for fichier in sorted(os.listdir(chemin_dossier)):
        if not fichier.lower().endswith(".pdf"):
            continue
        chemin = os.path.join(chemin_dossier, fichier)
        try:
            pages = extraire_pages(chemin)
            toutes_pages.extend(pages)
            print(f"  ✓ {fichier} — {len(pages)} pages extraites")
        except Exception as e:
            print(f"  ✗ {fichier} — erreur : {e}")

    return toutes_pages


def _nettoyer(texte: str) -> str:
    """Nettoie les espaces multiples, sauts de ligne superflus, etc."""
    texte = re.sub(r"[ \t]+", " ", texte)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    texte = re.sub(r" +\n", "\n", texte)
    return texte.strip()


if __name__ == "__main__":
    dossier = os.path.join(os.path.dirname(__file__), "..", "cnil")
    pages = ingerer_dossier(dossier)
    print(f"\nTotal : {len(pages)} pages extraites.")
