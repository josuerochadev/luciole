"""
Transcription audio — fonctionnalité désactivée.
Whisper est une API exclusive OpenAI, non disponible via Gemini.
"""


def transcrire_audio(chemin_audio: str) -> dict:
    raise NotImplementedError(
        "La transcription audio est désactivée (Whisper non disponible avec Gemini). "
        "Uploadez une image ou un PDF à la place."
    )
