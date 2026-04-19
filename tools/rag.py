"""
Module RAG v3 — embeddings OpenAI + similarité cosine numpy + BM25 + chunking.

Améliorations v3 (par rapport à v2) :
  - Chunking         : découpe les articles en chunks ~500 tokens avec overlap
  - Cache mémoire    : index + BM25 chargés 1 fois, invalidés sur mtime disque
  - Tokenisation BM25: stop words FR/EN + normalisation (plus de split() naïf)
  - Seuil de score   : filtre les résultats non pertinents (score_final < seuil)
  - Query expansion  : reformulation HyDE via LLM pour améliorer le recall
  - Contexte enrichi : 1000 chars de document retournés (au lieu de 300)
  - Déduplication     : regroupe les chunks d'un même article dans les résultats
"""
import functools
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import numpy as np

from config import DATA_DIR
from llm import get_openai_client, appeler_llm

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

try:
    import cohere
    HAS_COHERE = bool(os.getenv("COHERE_API_KEY"))
except ImportError:
    HAS_COHERE = False

logger = logging.getLogger(__name__)

EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.json")
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE      = 512          # Max inputs par appel OpenAI (limite : 2048)
FRESHNESS_DECAY  = 90           # Jours après lesquels un article est considéré "vieux"

# --- Chunking ---
CHUNK_SIZE       = 500          # Taille cible d'un chunk en tokens (~mots)
CHUNK_OVERLAP    = 80           # Overlap entre chunks consécutifs

# --- Score hybride ---
ALPHA_SEMANTIC   = 0.5          # Poids similarité cosine
ALPHA_BM25       = 0.25         # Poids BM25 (lexical)
ALPHA_FRAICHEUR  = 0.25         # Poids fraîcheur

# Fallback sans BM25
ALPHA_SIMILARITE_FALLBACK = 0.75
ALPHA_FRAICHEUR_FALLBACK  = 0.25

# Bonus feedback utilisateur
ALPHA_FEEDBACK = 0.1

# Seuil minimum de score pour retourner un résultat
SCORE_MINIMUM = 0.25

# --- Stop words FR/EN pour BM25 ---
_STOP_WORDS = frozenset(
    # Français
    "le la les un une des de du d l au aux en et est "
    "il elle on nous vous ils elles je tu ce cette ces "
    "qui que qu quoi dont où pour par sur dans avec "
    "ne pas plus son sa ses leur leurs mon ma mes "
    "tout tous toute toutes autre autres même aussi "
    "très bien fait être avoir été a ont sont sera sera "
    "peut comme mais ou car donc ni si se "
    # Anglais
    "the a an and or but in on at to for of is it "
    "this that these those was were be been has have had "
    "will would can could do does did not no with from by "
    "are am its his her their our your my we they he she "
    "so if then than up out about into over after".split()
)


# ---------------------------------------------------------------------------
# Tokenisation BM25 améliorée
# ---------------------------------------------------------------------------

def _tokenize(texte: str) -> list[str]:
    """Tokenise un texte : lowercase, suppression ponctuation, stop words."""
    mots = re.findall(r"[a-zà-ÿ0-9]+", texte.lower())
    return [m for m in mots if m not in _STOP_WORDS and len(m) > 1]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunker(texte: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Découpe un texte en chunks de ~chunk_size mots avec overlap.
    Retourne au moins 1 chunk même si le texte est court.
    """
    mots = texte.split()
    if len(mots) <= chunk_size:
        return [texte]

    chunks = []
    debut = 0
    while debut < len(mots):
        fin = debut + chunk_size
        chunk = " ".join(mots[debut:fin])
        chunks.append(chunk)
        debut += chunk_size - overlap

    return chunks


# ---------------------------------------------------------------------------
# Persistance avec cache mémoire
# ---------------------------------------------------------------------------

_index_cache: dict = {"data": None, "mtime": 0.0}
_bm25_cache: dict = {"bm25": None, "tokens": None, "index_mtime": 0.0}


def _charger_index() -> list[dict]:
    """Charge l'index avec cache mémoire invalidé par mtime du fichier."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(EMBEDDINGS_FILE):
        _index_cache["data"] = []
        _index_cache["mtime"] = 0.0
        return []

    mtime = os.path.getmtime(EMBEDDINGS_FILE)
    if _index_cache["data"] is not None and _index_cache["mtime"] == mtime:
        logger.debug("[RAG] Index servi depuis le cache mémoire.")
        return _index_cache["data"]

    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    _index_cache["data"] = data
    _index_cache["mtime"] = mtime
    logger.info(f"[RAG] Index chargé depuis le disque ({len(data)} entrées).")
    return data


def _invalider_cache() -> None:
    """Invalide le cache mémoire (après écriture)."""
    _index_cache["data"] = None
    _index_cache["mtime"] = 0.0
    _bm25_cache["bm25"] = None
    _bm25_cache["tokens"] = None
    _bm25_cache["index_mtime"] = 0.0


def _sauvegarder_index(index: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    _invalider_cache()


def _article_id(lien: str) -> str:
    return hashlib.sha256(lien.encode()).hexdigest()[:16]


def _chunk_id(lien: str, chunk_idx: int) -> str:
    return hashlib.sha256(f"{lien}::chunk::{chunk_idx}".encode()).hexdigest()[:16]


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


@functools.lru_cache(maxsize=128)
def _get_query_embedding(query: str) -> tuple[float, ...]:
    """Embedding de requête avec cache LRU (évite les appels API répétés)."""
    logger.info("[RAG] Cache miss — appel API embedding pour : '%s'", query[:80])
    return tuple(_embedder(query))


# ---------------------------------------------------------------------------
# Query expansion — HyDE (Hypothetical Document Embeddings)
# ---------------------------------------------------------------------------

def _expand_query(query: str) -> str:
    """
    Génère un paragraphe hypothétique qui répondrait à la requête.
    L'embedding de ce texte enrichi matche mieux les documents pertinents.
    """
    try:
        prompt = (
            "Tu es un assistant de veille technologique. "
            "Écris un court paragraphe (3-4 phrases) qui serait un extrait d'article "
            "répondant précisément à cette question. Sois factuel et technique. "
            "Ne mentionne pas que c'est hypothétique.\n\n"
            f"Question : {query}"
        )
        hypothetical = appeler_llm(prompt)
        expanded = f"{query}\n\n{hypothetical}"
        logger.info("[RAG] Query expansion HyDE effectuée (%d chars).", len(expanded))
        return expanded
    except Exception as e:
        logger.warning(f"[RAG] Query expansion échouée (fallback requête brute) : {e}")
        return query


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
# BM25 avec cache
# ---------------------------------------------------------------------------

def _get_bm25(candidats: list[dict]) -> "BM25Okapi | None":
    """Retourne l'index BM25 avec cache invalidé par mtime du fichier index."""
    if not HAS_BM25:
        return None

    mtime = _index_cache.get("mtime", 0.0)
    if _bm25_cache["bm25"] is not None and _bm25_cache["index_mtime"] == mtime:
        logger.debug("[RAG] BM25 servi depuis le cache mémoire.")
        return _bm25_cache["bm25"]

    tokens = [_tokenize(e.get("document", "")) for e in candidats]
    bm25 = BM25Okapi(tokens)

    _bm25_cache["bm25"] = bm25
    _bm25_cache["tokens"] = tokens
    _bm25_cache["index_mtime"] = mtime
    logger.info("[RAG] Index BM25 construit (%d documents).", len(candidats))
    return bm25


# ---------------------------------------------------------------------------
# Indexation batch avec chunking
# ---------------------------------------------------------------------------

def indexer_articles(articles: list[dict]) -> int:
    """
    Indexe une liste d'articles en batch avec chunking :
    - Découpe chaque article en chunks de ~500 mots avec overlap
    - 1 seul appel API pour tous les embeddings
    - 1 seule lecture + 1 seule écriture du fichier index

    Returns:
        Nombre de chunks indexés avec succès.
    """
    # Préparer les chunks valides
    chunks_a_indexer = []  # (article, texte_chunk, chunk_id, chunk_idx, total_chunks)
    for article in articles:
        lien = article.get("lien", "")
        if not lien:
            continue
        titre = article.get("titre", "")
        contenu = (
            article.get("contenu_complet")
            or article.get("resume")
            or article.get("resume_brut", "")
        )
        texte_complet = f"{titre}. {contenu}"[:5000].strip()
        if not texte_complet:
            continue

        chunks = _chunker(texte_complet)
        for i, chunk_text in enumerate(chunks):
            cid = _chunk_id(lien, i)
            chunks_a_indexer.append((article, chunk_text, cid, i, len(chunks)))

    if not chunks_a_indexer:
        return 0

    # --- 1 seul appel API pour tous les embeddings ---
    nb_articles = len({a.get("lien") for a, _, _, _, _ in chunks_a_indexer})
    logger.info(
        f"[RAG] Batch embedding : {len(chunks_a_indexer)} chunks "
        f"({nb_articles} articles) en {max(1, len(chunks_a_indexer)//BATCH_SIZE + 1)} appel(s) API"
    )
    try:
        textes = [t for _, t, _, _, _ in chunks_a_indexer]
        embeddings = _embedder_batch(textes)
    except Exception as e:
        logger.error(f"[RAG] Batch embedding échoué : {e}")
        return 0

    # --- 1 seule lecture de l'index ---
    index = _charger_index()
    # Supprimer les anciennes entrées des articles mis à jour
    liens_a_mettre_a_jour = {a.get("lien") for a, _, _, _, _ in chunks_a_indexer}
    index = [
        e for e in index
        if e["metadata"].get("lien", "") not in liens_a_mettre_a_jour
    ]

    ajouts = []
    for (article, chunk_text, cid, chunk_idx, total_chunks), embedding in zip(chunks_a_indexer, embeddings):
        ajouts.append({
            "id":        cid,
            "embedding": embedding,
            "document":  chunk_text,
            "metadata": {
                "titre":            article.get("titre", ""),
                "lien":             article.get("lien", ""),
                "categorie":        str(article.get("categorie", "Autre")),
                "pertinence":       int(article.get("pertinence", 0)),
                "date_publication": str(article.get("date_publication", "")),
                "source":           str(article.get("source", "")),
                "chunk_index":      chunk_idx,
                "total_chunks":     total_chunks,
            },
        })

    index.extend(ajouts)

    # --- 1 seule écriture ---
    _sauvegarder_index(index)
    logger.info(f"[RAG] {len(ajouts)} chunks indexés ({nb_articles} articles).")
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
    hyde: bool = True,
    rerank: bool = True,
) -> list[dict]:
    """
    Recherche sémantique avec filtrage, score hybride, chunking et HyDE.

    Args:
        query:          Question ou sujet en langage naturel.
        n:              Nombre maximum de résultats (articles, pas chunks).
        categorie:      Filtre sur la catégorie (ex: "IA", "Cloud").
        date_min:       Filtre sur la date ISO 8601 (ex: "2026-04-01").
        pertinence_min: Filtre sur le score de pertinence LLM (ex: 7).
        avec_fraicheur: Si True, intègre un score de fraîcheur au classement.
        hyde:           Si True, utilise HyDE pour enrichir la requête.
        rerank:         Si True et Cohere disponible, re-rank les résultats.

    Returns:
        Liste de dicts triés par score hybride décroissant, dédupliqués par article.
    """
    index = _charger_index()
    if not index:
        logger.warning("[RAG] Index vide.")
        return []

    # --- Filtrage par métadonnées ---
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

    logger.info(f"[RAG] Recherche : '{query}' sur {len(candidats)}/{len(index)} chunks")

    # --- Query expansion HyDE ---
    query_for_embedding = _expand_query(query) if hyde else query

    # --- Embedding de la requête (avec cache LRU) ---
    try:
        cached = _get_query_embedding.cache_info().hits
        query_vec = np.array(_get_query_embedding(query_for_embedding), dtype=np.float32)
        if _get_query_embedding.cache_info().hits > cached:
            logger.info("[RAG] Cache hit — embedding réutilisé pour : '%s'", query[:80])
    except Exception as e:
        logger.error(f"[RAG] Échec embedding requête : {e}")
        return []

    # --- Similarité cosine vectorisée (numpy) ---
    matrix = np.array([e["embedding"] for e in candidats], dtype=np.float32)
    normes = np.linalg.norm(matrix, axis=1)
    norme_query = np.linalg.norm(query_vec)

    normes_safe = np.where(normes == 0, 1e-10, normes)
    similarites = (matrix @ query_vec) / (normes_safe * norme_query)

    # --- Score BM25 (lexical) avec tokenisation améliorée ---
    scores_bm25_norm = np.zeros(len(candidats), dtype=np.float32)
    if HAS_BM25:
        corpus_tokens = [_tokenize(e.get("document", "")) for e in candidats]
        bm25 = BM25Okapi(corpus_tokens)
        query_tokens = _tokenize(query)
        if query_tokens:
            scores_bm25_raw = np.array(bm25.get_scores(query_tokens), dtype=np.float32)
            # Normalisation par rang (plus robuste que min-max)
            ranks = np.argsort(np.argsort(scores_bm25_raw)).astype(np.float32)
            scores_bm25_norm = ranks / max(len(candidats) - 1, 1)

    # --- Score hybride : cosine + BM25 + fraîcheur ---
    if avec_fraicheur:
        fraicheurs = np.array([
            _score_fraicheur(e["metadata"].get("date_publication", ""))
            for e in candidats
        ], dtype=np.float32)
        if HAS_BM25:
            scores = (ALPHA_SEMANTIC * similarites
                      + ALPHA_BM25 * scores_bm25_norm
                      + ALPHA_FRAICHEUR * fraicheurs)
        else:
            scores = (ALPHA_SIMILARITE_FALLBACK * similarites
                      + ALPHA_FRAICHEUR_FALLBACK * fraicheurs)
    else:
        if HAS_BM25:
            scores = ALPHA_SEMANTIC * similarites + ALPHA_BM25 * scores_bm25_norm
        else:
            scores = similarites

    # --- Bonus feedback utilisateur ---
    feedbacks = {}
    try:
        from tools.database import get_feedbacks_moyens
        feedbacks = get_feedbacks_moyens()
        if feedbacks:
            for i, entry in enumerate(candidats):
                url = entry["metadata"].get("lien", "")
                if url in feedbacks:
                    scores[i] += ALPHA_FEEDBACK * (feedbacks[url] / 10)
    except Exception as e:
        logger.warning(f"[RAG] Feedbacks indisponibles (non bloquant) : {e}")

    # --- Déduplication par article (garder le meilleur chunk par URL) ---
    indices_tries = np.argsort(scores)[::-1]
    articles_vus = {}  # lien → (idx, score)
    for idx in indices_tries:
        score = float(scores[idx])
        if score < SCORE_MINIMUM:
            break
        lien = candidats[idx]["metadata"].get("lien", "")
        if lien not in articles_vus:
            articles_vus[lien] = idx
        if len(articles_vus) >= n:
            break

    # --- Construction des résultats ---
    resultats = []
    for lien, idx in articles_vus.items():
        entry = candidats[idx]
        meta = entry["metadata"]

        # Collecter tous les chunks de cet article pour un contexte enrichi
        chunks_article = [
            e.get("document", "")
            for e in candidats
            if e["metadata"].get("lien", "") == lien
        ]
        contexte_enrichi = "\n\n".join(chunks_article)[:1500]

        resultats.append({
            "titre":              meta.get("titre", ""),
            "lien":               meta.get("lien", ""),
            "categorie":          meta.get("categorie", ""),
            "pertinence":         meta.get("pertinence", 0),
            "date_publication":   meta.get("date_publication", ""),
            "source":             meta.get("source", ""),
            "score_similarite":   round(float(similarites[idx]), 3),
            "score_bm25":         round(float(scores_bm25_norm[idx]), 3),
            "score_fraicheur":    round(float(_score_fraicheur(meta.get("date_publication", ""))), 3),
            "score_feedback":     round(float(ALPHA_FEEDBACK * (feedbacks.get(meta.get("lien", ""), 0) / 10)), 3),
            "score_final":        round(float(scores[idx]), 3),
            "resume_extrait":     contexte_enrichi,
            "chunks_utilises":    meta.get("total_chunks", 1),
        })

    # Trier par score final décroissant
    resultats.sort(key=lambda r: r["score_final"], reverse=True)

    # --- Re-ranking Cohere (M6E4) ---
    if rerank and HAS_COHERE and len(resultats) > 1:
        # Récupérer plus de résultats pour le re-ranking, puis affiner
        resultats = rerank_cohere(query, resultats, top_n=n)

    logger.info(f"[RAG] {len(resultats)} article(s) retourné(s) (seuil={SCORE_MINIMUM}).")
    return resultats


# ---------------------------------------------------------------------------
# Re-ranking Cohere (M6E4)
# ---------------------------------------------------------------------------

_cohere_client = None


def _get_cohere_client():
    """Client Cohere lazy init (singleton)."""
    global _cohere_client
    if _cohere_client is None and HAS_COHERE:
        _cohere_client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
    return _cohere_client


def rerank_cohere(query: str, resultats: list[dict], top_n: int = 5) -> list[dict]:
    """
    Re-rank les résultats RAG avec Cohere rerank-multilingual-v3.0.
    Fallback : retourne les résultats inchangés si Cohere est indisponible.
    """
    client = _get_cohere_client()
    if client is None or not resultats:
        return resultats[:top_n]

    docs = [r.get("resume_extrait", r.get("titre", "")) for r in resultats]

    try:
        response = client.rerank(
            model="rerank-multilingual-v3.0",
            query=query,
            documents=docs,
            top_n=min(top_n, len(docs)),
        )
        reranked = []
        for r in response.results:
            item = resultats[r.index].copy()
            item["rerank_score"] = round(r.relevance_score, 4)
            reranked.append(item)

        logger.info(f"[RAG] Reranking Cohere : {len(resultats)} → {len(reranked)} résultats")
        return reranked

    except Exception as e:
        logger.warning(f"[RAG] Reranking Cohere échoué (fallback sans rerank) : {e}")
        return resultats[:top_n]


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def taille_index() -> int:
    return len(_charger_index())


def vider_index() -> None:
    _sauvegarder_index([])
    logger.info("[RAG] Index vidé.")
