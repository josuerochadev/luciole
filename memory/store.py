"""
Gestion de la mémoire conversationnelle de l'agent.
Stocke les messages dans PostgreSQL (Neon).
Supporte aussi le chargement de contexte depuis l'historique conversations (database.py).
"""
import logging
import uuid
from datetime import datetime, timezone

from db_utils import connect as _get_connection, cursor as _cur

logger = logging.getLogger(__name__)

LIMITE_MEMOIRE = 50

_session_id: str = str(uuid.uuid4())

# Conversation active (optionnel, alimenté par l'API)
_active_conversation_id: str | None = None


def set_active_conversation(conv_id: str | None) -> None:
    """Définit la conversation active pour le contexte mémoire."""
    global _active_conversation_id
    _active_conversation_id = conv_id
    logger.debug(f"[memory] Conversation active : {conv_id}")


def _init_table(conn) -> None:
    """Crée la table memory_conversations si nécessaire."""
    cur = _cur(conn)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_conversations (
            id         SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            timestamp  TEXT NOT NULL
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_conversations(session_id)"
    )
    conn.commit()


def store(message: str, role: str = "user", conversation_id: str | None = None) -> None:
    """
    Ajoute un message en mémoire.

    Args:
        message:         Le contenu du message.
        role:            "user" ou "assistant".
        conversation_id: ID de conversation pour isoler la mémoire par utilisateur.
                         Si None, utilise le session_id global (mode CLI).
    """
    sid = conversation_id or _session_id
    conn = _get_connection()
    try:
        _init_table(conn)
        cur = _cur(conn)
        cur.execute(
            "INSERT INTO memory_conversations (session_id, role, content, timestamp)"
            " VALUES (%s, %s, %s, %s)",
            (sid, role, message, datetime.now(timezone.utc).isoformat()),
        )
        # Tronquer les messages les plus anciens au-delà de LIMITE_MEMOIRE
        cur.execute(
            """
            DELETE FROM memory_conversations
            WHERE session_id = %s AND id NOT IN (
                SELECT id FROM memory_conversations
                WHERE session_id = %s
                ORDER BY id DESC
                LIMIT %s
            )
            """,
            (sid, sid, LIMITE_MEMOIRE),
        )
        conn.commit()
        cur.execute(
            "SELECT COUNT(*) AS c FROM memory_conversations WHERE session_id = %s", (sid,)
        )
        count = cur.fetchone()["c"]
        logger.debug(f"[memory] store() — {count}/{LIMITE_MEMOIRE} messages. Role={role}, sid={sid[:8]}")
    finally:
        conn.close()


def recall(n: int = 20, conversation_id: str | None = None) -> list[dict]:
    """
    Retourne les n derniers messages de la session courante (du plus ancien au plus récent).

    Args:
        n:               Nombre de messages à rappeler (défaut : 20).
        conversation_id: ID de conversation pour isoler la mémoire par utilisateur.
                         Si None, utilise le session_id global (mode CLI).

    Returns:
        Liste de dicts {role, content}.
    """
    sid = conversation_id or _session_id
    conn = _get_connection()
    try:
        _init_table(conn)
        cur = _cur(conn)
        cur.execute(
            """
            SELECT role, content FROM memory_conversations
            WHERE session_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (sid, n),
        )
        rows = cur.fetchall()
        résultat = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        logger.debug(f"[memory] recall({n}) — {len(résultat)} message(s) retourné(s). sid={sid[:8]}")
        return résultat
    finally:
        conn.close()


def clear() -> None:
    """Supprime tous les messages de la session courante."""
    conn = _get_connection()
    try:
        _init_table(conn)
        cur = _cur(conn)
        cur.execute("DELETE FROM memory_conversations WHERE session_id = %s", (_session_id,))
        conn.commit()
        logger.debug("[memory] clear() — mémoire vidée.")
    finally:
        conn.close()


def taille() -> int:
    """Retourne le nombre de messages de la session courante."""
    conn = _get_connection()
    try:
        _init_table(conn)
        cur = _cur(conn)
        cur.execute(
            "SELECT COUNT(*) AS c FROM memory_conversations WHERE session_id = %s",
            (_session_id,),
        )
        return cur.fetchone()["c"]
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
        _init_table(conn)
        cur = _cur(conn)
        cur.execute(
            """
            SELECT session_id,
                   COUNT(*) AS msg_count,
                   MIN(timestamp) AS first_msg,
                   MAX(timestamp) AS last_msg
            FROM memory_conversations
            GROUP BY session_id
            ORDER BY first_msg DESC
            """
        )
        return [
            {
                "session_id": r["session_id"],
                "message_count": r["msg_count"],
                "first_message": r["first_msg"],
                "last_message": r["last_msg"],
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()
