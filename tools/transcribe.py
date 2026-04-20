"""
Outil multimodal — Option A : transcription audio via Whisper API.
Transcrit un fichier audio en français, puis analyse le contenu avec le LLM.
"""
import os
import logging

logger = logging.getLogger(__name__)


def transcrire_audio(chemin_audio: str) -> dict:
    """
    Transcrit un fichier audio avec l'API Whisper d'OpenAI,
    puis analyse le texte transcrit avec le LLM.

    Args:
        chemin_audio: Chemin vers le fichier audio (.mp3, .wav, .m4a, .webm, .mp4).

    Returns:
        dict avec 'transcription' (texte brut) et 'analyse' (résumé structuré).

    Raises:
        FileNotFoundError: Si le fichier audio n'existe pas.
        RuntimeError: Si l'appel API échoue.
    """
    from llm import get_openai_client, appeler_llm

    if not os.path.isfile(chemin_audio):
        raise FileNotFoundError(f"Fichier audio introuvable : {chemin_audio}")

    ext = os.path.splitext(chemin_audio)[1].lower()
    formats_supportes = {".mp3", ".wav", ".m4a", ".webm", ".mp4", ".mpeg", ".mpga", ".oga", ".ogg", ".flac"}
    if ext not in formats_supportes:
        raise ValueError(f"Format audio non supporté : {ext}. Formats acceptés : {formats_supportes}")

    logger.info(f"[Transcribe] Transcription de : {chemin_audio}")

    try:
        client = get_openai_client()
        with open(chemin_audio, "rb") as f:
            language = os.getenv("WHISPER_LANGUAGE")  # None = auto-détection
            kwargs = {"model": "whisper-1", "file": f}
            if language:
                kwargs["language"] = language
            response = client.audio.transcriptions.create(**kwargs)
        transcription = response.text
        logger.info(f"[Transcribe] Transcription OK — {len(transcription)} caractères")
    except Exception as e:
        raise RuntimeError(f"Erreur Whisper API : {e}") from e

    # Analyse du texte transcrit par le LLM
    prompt_analyse = (
        "Voici la transcription d'un fichier audio.\n"
        "Fournis une analyse structurée :\n"
        "1. **Résumé** : de quoi parle cet audio (2-3 phrases)\n"
        "2. **Points clés** : liste des informations importantes\n"
        "3. **Langue/ton** : formel, informel, technique, etc.\n\n"
        f"Transcription :\n{transcription}"
    )
    analyse = appeler_llm(prompt_analyse)

    return {
        "transcription": transcription,
        "analyse": analyse,
    }
