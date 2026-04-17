"""
Gestion de la mémoire conversationnelle de l'agent.
Stocke les messages dans une base SQLite persistante (DATA_DIR/memory.db).
"""
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DATA_DIR

logger = logging.getLogger(__name__)

LIMITE_MEMOIRE = 50

_DB_PATH = f"{DATA_DIR}/memory.db"
_session_id: str = str(uuid.uuid4())


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite et crée la table si nécessaire."""
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)"
    )
    conn.commit()
    return conn


def store(message: str, role: str = "user") -> None:
    """
    Ajoute un message en mémoire (INSERT dans SQLite).

    Args:
        message: Le contenu du message.
        role:    "user" ou "assistant".
    """
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (_session_id, role, message, datetime.now(timezone.utc).isoformat()),
        )
        # Tronquer les messages les plus anciens au-delà de LIMITE_MEMOIRE
        conn.execute(
            """
            DELETE FROM conversations
            WHERE session_id = ? AND id NOT IN (
                SELECT id FROM conversations
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (_session_id, _session_id, LIMITE_MEMOIRE),
        )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE session_id = ?", (_session_id,)
        ).fetchone()[0]
        logger.debug(f"[memory] store() — {count}/{LIMITE_MEMOIRE} messages. Role={role}")
    finally:
        conn.close()


def recall(n: int = 20) -> list[dict]:
    """
    Retourne les n derniers messages de la session courante (du plus ancien au plus récent).

    Args:
        n: Nombre de messages à rappeler (défaut : 20).

    Returns:
        Liste de dicts {role, content}.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT role, content FROM conversations
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (_session_id, n),
        ).fetchall()
        résultat = [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        logger.debug(f"[memory] recall({n}) — {len(résultat)} message(s) retourné(s).")
        return résultat
    finally:
        conn.close()


def clear() -> None:
    """Supprime tous les messages de la session courante."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (_session_id,))
        conn.commit()
        logger.debug("[memory] clear() — mémoire vidée.")
    finally:
        conn.close()


def taille() -> int:
    """Retourne le nombre de messages de la session courante."""
    conn = _get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE session_id = ?", (_session_id,)
        ).fetchone()[0]
        return count
    finally:
        conn.close()


def recall_all_sessions() -> list[dict]:
    """
    Liste toutes les sessions passées avec leur nombre de messages et date de début.

    Returns:
        Liste de dicts {session_id, message_count, first_message, last_message}.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT session_id, COUNT(*) as msg_count,
                   MIN(timestamp) as first_msg, MAX(timestamp) as last_msg
            FROM conversations
            GROUP BY session_id
            ORDER BY first_msg DESC
            """
        ).fetchall()
        return [
            {
                "session_id": r[0],
                "message_count": r[1],
                "first_message": r[2],
                "last_message": r[3],
            }
            for r in rows
        ]
    finally:
        conn.close()
