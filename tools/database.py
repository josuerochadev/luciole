"""
Outil de persistance locale : lecture/écriture JSON des articles et historique.
Base SQLite de test pour l'agent ReAct (exercice 3).
"""
import json
import os
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from config import (
    DATA_DIR, ARTICLES_FILE, HISTORIQUE_FILE, ARCHIVES_FILE, LOGS_FILE,
    RETENTION_ARTICLES_JOURS, RETENTION_LOGS_JOURS,
)

DB_TEST_PATH = f"{DATA_DIR}/test_clients.db"

logger = logging.getLogger(__name__)


def _assurer_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def charger_json(chemin: str) -> list | dict:
    """Charge un fichier JSON (liste ou dict). Retourne [] si absent."""
    if not os.path.exists(chemin):
        return []
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def sauvegarder_json(chemin: str, données) -> None:
    """Sauvegarde des données en JSON (indenté pour lisibilité)."""
    _assurer_data_dir()
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(données, f, ensure_ascii=False, indent=2)


def article_deja_traite(lien: str) -> bool:
    """Vérifie si un article (identifié par son URL) a déjà été traité."""
    articles = charger_json(ARTICLES_FILE)
    liens_connus = {a["lien"] for a in articles}
    archives = charger_json(ARCHIVES_FILE)
    liens_archives = {a["lien"] for a in archives}
    return lien in liens_connus or lien in liens_archives


def sauvegarder_articles(articles: list[dict]) -> int:
    """
    Ajoute les nouveaux articles au fichier articles.json
    et les indexe dans ChromaDB pour la recherche sémantique (RAG).

    Returns:
        Nombre d'articles effectivement ajoutés (doublons exclus).
    """
    existants = charger_json(ARTICLES_FILE)
    liens_existants = {a["lien"] for a in existants}

    nouveaux = [a for a in articles if a["lien"] not in liens_existants]
    sauvegarder_json(ARTICLES_FILE, existants + nouveaux)
    logger.info(f"{len(nouveaux)} nouveaux articles sauvegardés.")

    # Indexation RAG des nouveaux articles
    if nouveaux:
        try:
            from tools.rag import indexer_articles
            indexer_articles(nouveaux)
        except Exception as e:
            logger.warning(f"Indexation RAG échouée (non bloquant) : {e}")

    return len(nouveaux)


def enregistrer_envoi(destinataires: list[str], nb_articles: int) -> None:
    """Enregistre un envoi email dans l'historique."""
    historique = charger_json(HISTORIQUE_FILE)
    historique.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "destinataires": destinataires,
        "nb_articles": nb_articles,
    })
    sauvegarder_json(HISTORIQUE_FILE, historique)


def archiver_articles_traites(articles: list[dict]) -> None:
    """Déplace des articles de articles.json vers archives.json."""
    archives = charger_json(ARCHIVES_FILE)
    liens_à_archiver = {a["lien"] for a in articles}

    existants = charger_json(ARTICLES_FILE)
    restants = [a for a in existants if a["lien"] not in liens_à_archiver]
    à_archiver = [a for a in existants if a["lien"] in liens_à_archiver]

    sauvegarder_json(ARTICLES_FILE, restants)
    sauvegarder_json(ARCHIVES_FILE, archives + à_archiver)
    logger.info(f"{len(à_archiver)} articles archivés.")


def purger_donnees_perimees() -> None:
    """Supprime les données dépassant les durées de rétention RGPD."""
    maintenant = datetime.now(timezone.utc)

    # Purge des archives (90 jours)
    limite_articles = maintenant - timedelta(days=RETENTION_ARTICLES_JOURS)
    archives = charger_json(ARCHIVES_FILE)
    archives_valides = [
        a for a in archives
        if datetime.fromisoformat(a.get("date_publication", maintenant.isoformat())) > limite_articles
    ]
    sauvegarder_json(ARCHIVES_FILE, archives_valides)
    logger.info(f"Purge archives : {len(archives) - len(archives_valides)} entrées supprimées.")

    # Purge des logs (30 jours)
    if not os.path.exists(LOGS_FILE):
        return
    limite_logs = maintenant - timedelta(days=RETENTION_LOGS_JOURS)
    logs_valides = []
    with open(LOGS_FILE, "r", encoding="utf-8") as f:
        for ligne in f:
            try:
                log = json.loads(ligne)
                if datetime.fromisoformat(log.get("date", maintenant.isoformat())) > limite_logs:
                    logs_valides.append(ligne)
            except json.JSONDecodeError:
                pass
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        f.writelines(logs_valides)
    logger.info("Purge logs terminée.")


# ---------------------------------------------------------------------------
# Base SQLite de test — agent ReAct
# ---------------------------------------------------------------------------

def _init_db() -> None:
    """
    Crée la base SQLite de test et insère 3 clients fictifs si elle n'existe pas.
    Idempotent : sans effet si la table existe déjà.
    """
    _assurer_data_dir()
    conn = sqlite3.connect(DB_TEST_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id      INTEGER PRIMARY KEY,
            nom     TEXT NOT NULL,
            email   TEXT NOT NULL,
            type    TEXT NOT NULL CHECK(type IN ('Premium', 'Standard')),
            depuis  TEXT NOT NULL
        )
    """)
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO clients (nom, email, type, depuis) VALUES (?, ?, ?, ?)",
            [
                ("Alice Martin",  "alice.martin@example.com",  "Premium",  "2023-01-15"),
                ("Bob Dupont",    "bob.dupont@example.com",    "Standard", "2024-03-20"),
                ("Claire Lemaire","claire.lemaire@example.com","Premium",  "2022-11-05"),
            ],
        )
        conn.commit()
        logger.info("[query_db] Base de test initialisée avec 3 clients fictifs.")
    conn.close()


def query_db(sql: str) -> list[dict]:
    """
    Exécute une requête SQL SELECT sur la base de test et retourne les résultats.
    ATTENTION : réservé aux tests — ne jamais exposer cette fonction à des
    entrées utilisateur non validées en production (risque d'injection SQL).

    Args:
        sql: Requête SQL SELECT à exécuter.

    Returns:
        Liste de dicts représentant les lignes retournées.

    Raises:
        ValueError: Si la requête n'est pas un SELECT.
        RuntimeError: En cas d'erreur SQLite.
    """
    _init_db()

    sql_propre = sql.strip()
    if not sql_propre.upper().startswith("SELECT"):
        raise ValueError(f"Seules les requêtes SELECT sont autorisées. Reçu : {sql_propre[:50]}")

    logger.info(f"[query_db] Exécution : {sql_propre}")
    try:
        conn = sqlite3.connect(DB_TEST_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql_propre)
        lignes = [dict(row) for row in cur.fetchall()]
        conn.close()
        logger.info(f"[query_db] {len(lignes)} ligne(s) retournée(s).")
        return lignes
    except sqlite3.Error as e:
        raise RuntimeError(f"Erreur SQLite : {e}") from e


# ---------------------------------------------------------------------------
# Feedbacks utilisateur — amélioration continue de la pertinence RAG
# ---------------------------------------------------------------------------

FEEDBACKS_DB_PATH = os.path.join(DATA_DIR, "feedbacks.db")


def _init_feedbacks_db() -> None:
    """Crée la table feedbacks si elle n'existe pas."""
    _assurer_data_dir()
    conn = sqlite3.connect(FEEDBACKS_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            article_url TEXT NOT NULL,
            score_user  INTEGER NOT NULL CHECK(score_user BETWEEN 1 AND 10),
            timestamp   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def noter_article(url: str, score: int) -> dict:
    """
    Enregistre un feedback utilisateur pour un article.

    Args:
        url:   URL de l'article noté.
        score: Note de 1 à 10.

    Returns:
        Dict de confirmation.
    """
    if not 1 <= score <= 10:
        raise ValueError("Le score doit être entre 1 et 10.")
    _init_feedbacks_db()
    conn = sqlite3.connect(FEEDBACKS_DB_PATH)
    conn.execute(
        "INSERT INTO feedbacks (article_url, score_user, timestamp) VALUES (?, ?, ?)",
        (url, score, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    logger.info(f"[feedback] Article noté {score}/10 : {url}")
    return {"article_url": url, "score": score, "status": "enregistré"}


def get_feedbacks_moyens() -> dict[str, float]:
    """
    Retourne un dict {article_url: score_moyen} pour tous les articles notés.
    """
    _init_feedbacks_db()
    conn = sqlite3.connect(FEEDBACKS_DB_PATH)
    rows = conn.execute(
        "SELECT article_url, AVG(score_user) FROM feedbacks GROUP BY article_url"
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def ajouter_log(niveau: str, message: str, extra: dict = None) -> None:
    """Ajoute une entrée de log structuré en JSONL."""
    _assurer_data_dir()
    entree = {
        "date": datetime.now(timezone.utc).isoformat(),
        "niveau": niveau,
        "message": message,
        **(extra or {}),
    }
    with open(LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
