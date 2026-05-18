"""
Outil de persistance : lecture/écriture JSON des métadonnées d'envois,
et base PostgreSQL (Neon) pour les articles, feedbacks et la base de test ReAct.
"""
import json
import os
import sqlite3
import logging
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras

from config import (
    DATA_DIR, ARTICLES_FILE, HISTORIQUE_FILE, ARCHIVES_FILE, LOGS_FILE,
    RETENTION_ARTICLES_JOURS, RETENTION_LOGS_JOURS, DATABASE_URL,
)

# Base SQLite locale uniquement pour la démo agent ReAct (données fictives)
DB_TEST_PATH = f"{DATA_DIR}/test_clients.db"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers PostgreSQL
# ---------------------------------------------------------------------------

def _pg_connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(DATABASE_URL)


def _cur(conn) -> psycopg2.extras.RealDictCursor:
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ---------------------------------------------------------------------------
# Utilitaires JSON (historique envois, logs)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Table articles — PostgreSQL (Neon)
# ---------------------------------------------------------------------------

def _init_articles_table(conn) -> None:
    """Crée la table articles si elle n'existe pas."""
    cur = _cur(conn)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            lien             TEXT PRIMARY KEY,
            titre            TEXT NOT NULL,
            resume_brut      TEXT DEFAULT '',
            resume           TEXT DEFAULT '',
            contenu_complet  TEXT DEFAULT '',
            categorie        TEXT DEFAULT 'Autre',
            pertinence       INTEGER DEFAULT 0,
            action           TEXT DEFAULT 'lire',
            source           TEXT DEFAULT '',
            source_url       TEXT DEFAULT '',
            date_publication TEXT DEFAULT '',
            date_ajout       TEXT NOT NULL,
            archive          INTEGER DEFAULT 0
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_archive ON articles(archive)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date_publication)"
    )
    conn.commit()


def _migrer_json_vers_postgres() -> None:
    """Migration one-shot : importe articles.json et archives.json dans PostgreSQL."""
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)
        cur.execute("SELECT COUNT(*) AS c FROM articles")
        count = cur.fetchone()["c"]
        if count > 0:
            return  # déjà migré

        for fichier, is_archive in [(ARTICLES_FILE, 0), (ARCHIVES_FILE, 1)]:
            articles = charger_json(fichier)
            if articles:
                _insert_articles_pg(conn, articles, archive=is_archive)
                logger.info(f"Migration : {len(articles)} articles importés depuis {fichier}")
    finally:
        conn.close()


def _insert_articles_pg(conn, articles: list[dict], archive: int = 0) -> int:
    """Insère des articles dans PostgreSQL (ignore les doublons par lien)."""
    cur = _cur(conn)
    now = datetime.now(timezone.utc).isoformat()
    inseres = 0
    for a in articles:
        lien = a.get("lien", "")
        if not lien:
            continue
        try:
            cur.execute(
                """
                INSERT INTO articles
                    (lien, titre, resume_brut, resume, contenu_complet, categorie,
                     pertinence, action, source, source_url, date_publication, date_ajout, archive)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (lien) DO NOTHING
                """,
                (
                    lien,
                    a.get("titre", ""),
                    a.get("resume_brut", ""),
                    a.get("resume", ""),
                    a.get("contenu_complet", ""),
                    a.get("categorie", "Autre"),
                    int(a.get("pertinence", 0)),
                    a.get("action", "lire"),
                    a.get("source", ""),
                    a.get("source_url", ""),
                    a.get("date_publication", ""),
                    a.get("date_ajout", now),
                    archive,
                ),
            )
            inseres += cur.rowcount
        except psycopg2.Error as e:
            logger.debug(f"Insert échoué pour {lien} : {e}")
    conn.commit()
    return inseres


def article_deja_traite(lien: str) -> bool:
    """Vérifie si un article (identifié par son URL) existe déjà en base."""
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        _migrer_json_vers_postgres()
        cur = _cur(conn)
        cur.execute("SELECT 1 FROM articles WHERE lien = %s", (lien,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def sauvegarder_articles(articles: list[dict]) -> int:
    """
    Ajoute les nouveaux articles dans PostgreSQL et les indexe dans le RAG.

    Returns:
        Nombre d'articles effectivement ajoutés (doublons exclus).
    """
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)
        now = datetime.now(timezone.utc).isoformat()
        nouveaux = []

        for a in articles:
            lien = a.get("lien", "")
            if not lien:
                continue
            cur.execute("SELECT 1 FROM articles WHERE lien = %s", (lien,))
            if cur.fetchone():
                continue
            cur.execute(
                """
                INSERT INTO articles
                    (lien, titre, resume_brut, resume, contenu_complet, categorie,
                     pertinence, action, source, source_url, date_publication, date_ajout, archive)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                """,
                (
                    lien,
                    a.get("titre", ""),
                    a.get("resume_brut", ""),
                    a.get("resume", ""),
                    a.get("contenu_complet", ""),
                    a.get("categorie", "Autre"),
                    int(a.get("pertinence", 0)),
                    a.get("action", "lire"),
                    a.get("source", ""),
                    a.get("source_url", ""),
                    a.get("date_publication", ""),
                    now,
                ),
            )
            nouveaux.append(a)

        conn.commit()
    finally:
        conn.close()

    logger.info(f"{len(nouveaux)} nouveaux articles sauvegardés en PostgreSQL.")

    # Indexation RAG des nouveaux articles
    if nouveaux:
        try:
            from tools.rag import indexer_articles
            indexer_articles(nouveaux)
        except Exception as e:
            logger.warning(f"Indexation RAG échouée (non bloquant) : {e}")

    return len(nouveaux)


def lire_articles_actifs() -> list[dict]:
    """
    Retourne tous les articles non archivés depuis PostgreSQL.
    Utilisé pour reconstruire l'index RAG après un redéploiement.
    """
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)
        cur.execute(
            "SELECT lien, titre, resume, contenu_complet, categorie, pertinence,"
            "       source, date_publication"
            " FROM articles WHERE archive = 0 ORDER BY date_ajout DESC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


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
    """Marque des articles comme archivés dans PostgreSQL."""
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)
        for a in articles:
            lien = a.get("lien")
            if lien:
                cur.execute("UPDATE articles SET archive = 1 WHERE lien = %s", (lien,))
        conn.commit()
    finally:
        conn.close()
    logger.info(f"{len(articles)} articles archivés.")


def purger_donnees_perimees() -> None:
    """Supprime les données dépassant les durées de rétention RGPD."""
    maintenant = datetime.now(timezone.utc)

    # Purge des archives PostgreSQL (90 jours)
    limite_articles = (maintenant - timedelta(days=RETENTION_ARTICLES_JOURS)).isoformat()
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)
        cur.execute(
            "DELETE FROM articles WHERE archive = 1 AND date_publication < %s",
            (limite_articles,),
        )
        conn.commit()
        logger.info(f"Purge archives PostgreSQL : {cur.rowcount} entrées supprimées.")
    finally:
        conn.close()

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
# Base SQLite de test — agent ReAct (données fictives, recréées au démarrage)
# ---------------------------------------------------------------------------

def _init_db() -> None:
    """
    Crée la base SQLite de test et insère 3 clients fictifs si elle n'existe pas.
    Idempotent : sans effet si la table existe déjà.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
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
                ("Alice Martin",   "alice.martin@example.com",   "Premium",  "2023-01-15"),
                ("Bob Dupont",     "bob.dupont@example.com",     "Standard", "2024-03-20"),
                ("Claire Lemaire", "claire.lemaire@example.com", "Premium",  "2022-11-05"),
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

    # Ajouter un LIMIT si absent pour éviter les résultats non bornés
    if "LIMIT" not in sql_propre.upper():
        sql_propre += " LIMIT 1000"

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
# Feedbacks utilisateur — PostgreSQL (Neon)
# ---------------------------------------------------------------------------

def _init_feedbacks_table(conn) -> None:
    """Crée la table feedbacks si elle n'existe pas."""
    cur = _cur(conn)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_feedbacks (
            id          SERIAL PRIMARY KEY,
            article_url TEXT NOT NULL,
            score_user  INTEGER NOT NULL CHECK(score_user BETWEEN 1 AND 10),
            timestamp   TEXT NOT NULL
        )
    """)
    conn.commit()


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
    conn = _pg_connect()
    try:
        _init_feedbacks_table(conn)
        cur = _cur(conn)
        cur.execute(
            "INSERT INTO article_feedbacks (article_url, score_user, timestamp) VALUES (%s, %s, %s)",
            (url, score, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info(f"[feedback] Article noté {score}/10 : {url}")
    return {"article_url": url, "score": score, "status": "enregistré"}


def get_feedbacks_moyens() -> dict[str, float]:
    """
    Retourne un dict {article_url: score_moyen} pour tous les articles notés.
    """
    conn = _pg_connect()
    try:
        _init_feedbacks_table(conn)
        cur = _cur(conn)
        cur.execute(
            "SELECT article_url, AVG(score_user) AS avg_score"
            " FROM article_feedbacks GROUP BY article_url"
        )
        return {row["article_url"]: float(row["avg_score"]) for row in cur.fetchall()}
    finally:
        conn.close()


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
