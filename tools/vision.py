"""
Outil multimodal — Option B : analyse d'image/PDF via GPT-4o Vision.
Envoie une image (facture, ticket, formulaire...) ou un PDF et extrait les informations en JSON.
"""
import base64
import json
import os
import re
import logging

logger = logging.getLogger(__name__)

FORMATS_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
FORMATS_SUPPORTES = FORMATS_IMAGE | {".pdf"}

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _pdf_to_base64(chemin_pdf: str) -> tuple[str, str]:
    """Convertit la première page d'un PDF en image PNG base64."""
    import fitz  # pymupdf

    doc = fitz.open(chemin_pdf)
    page = doc[0]
    pix = page.get_pixmap(dpi=200)
    image_bytes = pix.tobytes("png")
    doc.close()
    logger.info(f"[Vision] PDF converti en image PNG ({len(image_bytes)} octets)")
    return base64.b64encode(image_bytes).decode("utf-8"), "image/png"


def analyser_image(chemin_image: str, consigne: str = None) -> dict:
    """
    Analyse une image avec GPT-4o Vision et extrait les informations en JSON.

    Args:
        chemin_image: Chemin vers le fichier image.
        consigne: Instruction spécifique (ex: "Extrais les montants de cette facture").
                  Si None, utilise une consigne générique d'extraction.

    Returns:
        dict avec les informations extraites de l'image.

    Raises:
        FileNotFoundError: Si le fichier image n'existe pas.
        RuntimeError: Si l'appel API échoue.
    """
    from llm import get_openai_client
    from config import MODEL_VISION

    if not os.path.isfile(chemin_image):
        raise FileNotFoundError(f"Fichier image introuvable : {chemin_image}")

    ext = os.path.splitext(chemin_image)[1].lower()
    if ext not in FORMATS_SUPPORTES:
        raise ValueError(f"Format non supporté : {ext}. Formats acceptés : {FORMATS_SUPPORTES}")

    # Encodage base64 (PDF → conversion première page, image → lecture directe)
    if ext == ".pdf":
        image_b64, mime_type = _pdf_to_base64(chemin_image)
    else:
        with open(chemin_image, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        mime_type = MIME_TYPES[ext]
    logger.info(f"[Vision] Analyse de : {chemin_image} ({mime_type})")

    if consigne is None:
        consigne = (
            "Analyse ce document (facture, ticket, formulaire, ou autre). "
            "Extrais toutes les informations clés et retourne-les en JSON structuré."
        )

    prompt_text = (
        f"{consigne}\n\n"
        "RÈGLES :\n"
        "- Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après.\n"
        "- Adapte les clés JSON au type de document détecté.\n"
        "- Si un champ est illisible, indique 'illisible'.\n"
        "- Inclus un champ 'type_document' (facture, ticket, formulaire, photo, autre)."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=MODEL_VISION,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Luciole, un agent de veille technologique. "
                        "Tu analyses des images et documents visuels pour en extraire "
                        "des informations structurées. Réponds toujours en français."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=1024,
            timeout=60,
        )
        texte_brut = response.choices[0].message.content.strip()
        logger.info(f"[Vision] Réponse reçue — {len(texte_brut)} caractères")
    except Exception as e:
        raise RuntimeError(f"Erreur GPT-4o Vision : {e}") from e

    # Parsing JSON (même stratégie que llm.py)
    try:
        return json.loads(texte_brut)
    except json.JSONDecodeError:
        pass

    texte_propre = re.sub(r"```(?:json)?", "", texte_brut).strip().strip("`").strip()
    try:
        return json.loads(texte_propre)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", texte_brut, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("[Vision] Impossible de parser le JSON — retour du texte brut")
    return {"type_document": "erreur_parsing", "contenu_brut": texte_brut}
