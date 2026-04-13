"""
Module RAG — embeddings OpenAI + similarité cosine numpy.
Améliorations v2 :
  - Batch embeddings    : 1 appel API pour N articles (au lieu de N appels)
  - Index chargé 1 fois : lecture/écriture disque unique par opération batch
  - Similarité vectorisée : numpy matrix ops au lieu d'une boucle Python
  - Filtrage par métadonnées : catégorie, date, pertinence
  - Score hybride : similarité cosine + fraîcheur de l'article
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

import numpy as np

from config import DATA_DIR
from llm import get_openai_client

logger = logging.getLogger(__name__)

EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.json")
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE      = 512          # Max inputs par appel OpenAI (limite : 2048)
FRESHNESS_DECAY = 90           # Jours après lesquels un article est considéré "vieux"
ALPHA_SIMILARITE = 0.75        # Poids similarité cosine dans le score hybride
ALPHA_FRAICHEUR  = 0.25        # Poids fraîcheur dans le score hybride

# ---------------------------------------------------------------------------
# Persistance
# ---------------------------------------------------------------------------

def _charger_index() -> list[dict]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(EMBEDDINGS_FILE):
        return []
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _sauvegarder_index(index: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def _article_id(lien: str) -> str:
    return hashlib.sha256(lien.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Embeddings — batch
# ---------------------------------------------------------------------------

def _embedder_batch(textes: list[str]) -> list[list[float]]:
    """
    Calcule les embeddings de plusieurs textes en un seul appel API.
    Découpe automatiquement en chunks si len(textes) > BATCH_SIZE.
    """
    tous = []
    for i in range(0, len(textes), BATCH_SIZE):
        chunk = textes[i:i + BATCH_SIZE]
        response = get_openai_client().embeddings.create(
            input=chunk,
            model=EMBEDDING_MODEL,
        )
        tous.extend([item.embedding for item in response.data])
    return tous


def _embedder(texte: str) -> list[float]:
    """Embedding d'un texte unique (pour les requêtes de recherche)."""
    return _embedder_batch([texte])[0]


# ---------------------------------------------------------------------------
# Score de fraîcheur
# ---------------------------------------------------------------------------

def _score_fraicheur(date_str: str) -> float:
    """
    Retourne un score entre 0 et 1 selon l'âge de l'article.
    1.0 = publié aujourd'hui, décroît linéairement jusqu'à 0 à FRESHNESS_DECAY jours.
    """
    if not date_str:
        return 0.5  # Score neutre si date inconnue
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        jours = (datetime.now(timezone.utc) - date).days
        return max(0.0, 1.0 - jours / FRESHNESS_DECAY)
    except (ValueError, TypeError):
        return 0.5


# ---------------------------------------------------------------------------
# Indexation batch
# ---------------------------------------------------------------------------

def indexer_articles(articles: list[dict]) -> int:
    """
    Indexe une liste d'articles en batch :
    - 1 seul appel API pour tous les embeddings
    - 1 seule lecture + 1 seule écriture du fichier index

    Returns:
        Nombre d'articles indexés avec succès.
    """
    # Préparer les textes valides
    valides = []
    for article in articles:
        lien = article.get("lien", "")
        if not lien:
            continue
        titre  = article.get("titre", "")
        resume = article.get("resume", article.get("resume_brut", ""))
        texte  = f"{titre}. {resume}"[:3000].strip()
        if texte:
            valides.append((article, texte, _article_id(lien)))

    if not valides:
        return 0

    # --- 1 seul appel API pour tous les embeddings ---
    logger.info(f"[RAG] Batch embedding : {len(valides)} articles en {max(1, len(valides)//BATCH_SIZE + 1)} appel(s) API")
    try:
        textes    = [t for _, t, _ in valides]
        embeddings = _embedder_batch(textes)
    except Exception as e:
        logger.error(f"[RAG] Batch embedding échoué : {e}")
        return 0

    # --- 1 seule lecture de l'index ---
    index = _charger_index()
    ids_existants = {e["id"] for e in index}

    ajouts = []
    for (article, texte, doc_id), embedding in zip(valides, embeddings):
        # Upsert : supprimer l'ancienne version si elle existe
        if doc_id in ids_existants:
            index = [e for e in index if e["id"] != doc_id]

        ajouts.append({
            "id":        doc_id,
            "embedding": embedding,
            "document":  texte[:500],
            "metadata": {
                "titre":            article.get("titre", ""),
                "lien":             article.get("lien", ""),
                "categorie":        str(article.get("categorie", "Autre")),
                "pertinence":       int(article.get("pertinence", 0)),
                "date_publication": str(article.get("date_publication", "")),
                "source":           str(article.get("source", "")),
            },
        })

    index.extend(ajouts)

    # --- 1 seule écriture ---
    _sauvegarder_index(index)
    logger.info(f"[RAG] {len(ajouts)} articles indexés.")
    return len(ajouts)


def indexer_article(article: dict) -> None:
    """Indexe un article unique (délègue à indexer_articles)."""
    indexer_articles([article])


# ---------------------------------------------------------------------------
# Recherche sémantique améliorée
# ---------------------------------------------------------------------------

def rechercher_articles(
    query: str,
    n: int = 5,
    categorie: str | None = None,
    date_min: str | None = None,
    pertinence_min: int | None = None,
    avec_fraicheur: bool = True,
) -> list[dict]:
    """
    Recherche sémantique avec filtrage par métadonnées et score hybride.

    Args:
        query:          Question ou sujet en langage naturel.
        n:              Nombre maximum de résultats.
        categorie:      Filtre sur la catégorie (ex: "IA", "Cloud").
        date_min:       Filtre sur la date ISO 8601 (ex: "2026-04-01").
        pertinence_min: Filtre sur le score de pertinence LLM (ex: 7).
        avec_fraicheur: Si True, intègre un score de fraîcheur au classement.

    Returns:
        Liste de dicts triés par score hybride décroissant.
    """
    index = _charger_index()
    if not index:
        logger.warning("[RAG] Index vide.")
        return []

    # --- Filtrage par métadonnées ---
    # Exclure systématiquement les articles hors-sujet (pertinence trop faible)
    candidats = [e for e in index if e["metadata"].get("categorie", "").lower() != "hors-sujet"]
    if categorie:
        candidats = [e for e in candidats if categorie.lower() in e["metadata"].get("categorie", "").lower()]
    if date_min:
        candidats = [e for e in candidats if e["metadata"].get("date_publication", "") >= date_min]
    if pertinence_min is not None:
        candidats = [e for e in candidats if int(e["metadata"].get("pertinence", 0)) >= pertinence_min]

    if not candidats:
        logger.info("[RAG] Aucun article après filtrage des métadonnées.")
        return []

    logger.info(f"[RAG] Recherche : '{query}' sur {len(candidats)}/{len(index)} articles")

    # --- Embedding de la requête ---
    try:
        query_vec = np.array(_embedder(query), dtype=np.float32)
    except Exception as e:
        logger.error(f"[RAG] Échec embedding requête : {e}")
        return []

    # --- Similarité cosine vectorisée (numpy) ---
    # Charge toute la matrice en une opération au lieu d'une boucle Python
    matrix = np.array([e["embedding"] for e in candidats], dtype=np.float32)
    normes = np.linalg.norm(matrix, axis=1)
    norme_query = np.linalg.norm(query_vec)

    # Éviter la division par zéro
    normes_safe = np.where(normes == 0, 1e-10, normes)
    similarites = (matrix @ query_vec) / (normes_safe * norme_query)

    # --- Score hybride : similarité + fraîcheur ---
    if avec_fraicheur:
        fraicheurs = np.array([
            _score_fraicheur(e["metadata"].get("date_publication", ""))
            for e in candidats
        ], dtype=np.float32)
        scores = ALPHA_SIMILARITE * similarites + ALPHA_FRAICHEUR * fraicheurs
    else:
        scores = similarites

    # --- Top N ---
    indices_top = np.argsort(scores)[::-1][:n]

    resultats = []
    for idx in indices_top:
        entry = candidats[idx]
        meta  = entry["metadata"]
        resultats.append({
            "titre":              meta.get("titre", ""),
            "lien":               meta.get("lien", ""),
            "categorie":          meta.get("categorie", ""),
            "pertinence":         meta.get("pertinence", 0),
            "date_publication":   meta.get("date_publication", ""),
            "source":             meta.get("source", ""),
            "score_similarite":   round(float(similarites[idx]), 3),
            "score_fraicheur":    round(float(_score_fraicheur(meta.get("date_publication", ""))), 3),
            "score_final":        round(float(scores[idx]), 3),
            "resume_extrait":     entry.get("document", "")[:300],
        })

    logger.info(f"[RAG] {len(resultats)} résultat(s) retourné(s).")
    return resultats


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def taille_index() -> int:
    return len(_charger_index())


def vider_index() -> None:
    _sauvegarder_index([])
    logger.info("[RAG] Index vidé.")
