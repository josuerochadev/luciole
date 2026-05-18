"""
Persistance PostgreSQL pour l'historique des conversations.
Tables : users, conversations, messages, response_feedback.
"""
import uuid
from datetime import datetime, timezone

from db_utils import connect as _get_connection, cursor as _cur


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = _get_connection()
    try:
        cur = _cur(conn)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name  TEXT,
                created_at    TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                title      TEXT,
                user_id    TEXT REFERENCES users(id),
                created_at TEXT,
                updated_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                tokens_used     INTEGER,
                latency_ms      INTEGER,
                created_at      TEXT
            )
        """)

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS response_feedback (
                id         TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                rating     TEXT NOT NULL CHECK(rating IN ('up', 'down')),
                comment    TEXT,
                created_at TEXT
            )
        """)

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_response_feedback_msg ON response_feedback(message_id)"
        )

        # Migration: add user_id column if missing (existing databases)
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'conversations' AND column_name = 'user_id'
        """)
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE conversations ADD COLUMN user_id TEXT REFERENCES users(id)"
            )

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"
        )
        conn.commit()
    finally:
        conn.close()


def create_user(email: str, password_hash: str, display_name: str | None = None) -> dict:
    """Crée un nouvel utilisateur."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "INSERT INTO users (id, email, password_hash, display_name, created_at)"
            " VALUES (%s, %s, %s, %s, %s)",
            (user_id, email.lower().strip(), password_hash, display_name, now),
        )
        conn.commit()
        return {"id": user_id, "email": email.lower().strip(), "display_name": display_name, "created_at": now}
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Retourne un utilisateur par son email, ou None."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "SELECT id, email, password_hash, display_name, created_at FROM users WHERE email = %s",
            (email.lower().strip(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    """Retourne un utilisateur par son ID, ou None."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_conversation(title: str | None = None, user_id: str | None = None) -> dict:
    """Crée une nouvelle conversation et retourne ses métadonnées."""
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "INSERT INTO conversations (id, title, user_id, created_at, updated_at)"
            " VALUES (%s, %s, %s, %s, %s)",
            (conv_id, title, user_id, now, now),
        )
        conn.commit()
        return {"id": conv_id, "title": title, "user_id": user_id, "created_at": now, "updated_at": now}
    finally:
        conn.close()


def list_conversations(user_id: str | None = None) -> list[dict]:
    """Liste les conversations d'un utilisateur, triées par updated_at DESC."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        if user_id:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM conversations"
                " WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            )
        else:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM conversations"
                " WHERE user_id IS NULL ORDER BY updated_at DESC"
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_conversation(conv_id: str) -> dict | None:
    """Retourne une conversation par son ID, ou None."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s",
            (conv_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_conversation_messages(conv_id: str) -> list[dict]:
    """Retourne tous les messages d'une conversation (ordre chronologique)."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "SELECT id, role, content, tokens_used, latency_ms, created_at"
            " FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conv_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def add_message(
    conv_id: str,
    role: str,
    content: str,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
) -> dict:
    """Ajoute un message à une conversation et met à jour updated_at."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "INSERT INTO messages"
            " (id, conversation_id, role, content, tokens_used, latency_ms, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (msg_id, conv_id, role, content, tokens_used, latency_ms, now),
        )
        cur.execute(
            "UPDATE conversations SET updated_at = %s WHERE id = %s",
            (now, conv_id),
        )
        conn.commit()
        return {
            "id": msg_id,
            "conversation_id": conv_id,
            "role": role,
            "content": content,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "created_at": now,
        }
    finally:
        conn.close()


def delete_conversation(conv_id: str) -> bool:
    """Supprime une conversation et ses messages. Retourne True si elle existait."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute("DELETE FROM conversations WHERE id = %s", (conv_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_conversation_title(conv_id: str, title: str) -> bool:
    """Met à jour le titre d'une conversation. Retourne True si elle existait."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "UPDATE conversations SET title = %s, updated_at = %s WHERE id = %s",
            (title, now, conv_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_recent_messages(conv_id: str, n: int = 20) -> list[dict]:
    """Retourne les N derniers messages d'une conversation (pour le contexte LLM)."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s"
            " ORDER BY created_at DESC LIMIT %s",
            (conv_id, n),
        )
        rows = cur.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()


def save_response_feedback(message_id: str, rating: str, comment: str | None = None) -> dict:
    """Sauvegarde un feedback sur une réponse (up/down)."""
    fb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        cur = _cur(conn)
        # Upsert: remplace le feedback existant pour ce message
        cur.execute("DELETE FROM response_feedback WHERE message_id = %s", (message_id,))
        cur.execute(
            "INSERT INTO response_feedback (id, message_id, rating, comment, created_at)"
            " VALUES (%s, %s, %s, %s, %s)",
            (fb_id, message_id, rating, comment, now),
        )
        conn.commit()
        return {"id": fb_id, "message_id": message_id, "rating": rating, "comment": comment, "created_at": now}
    finally:
        conn.close()


def get_response_feedback_stats() -> dict:
    """Stats globales des feedbacks sur les réponses."""
    conn = _get_connection()
    try:
        cur = _cur(conn)
        cur.execute("SELECT COUNT(*) AS c FROM response_feedback")
        total = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM response_feedback WHERE rating = 'up'")
        up = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM response_feedback WHERE rating = 'down'")
        down = cur.fetchone()["c"]
        pct_positive = round((up / total) * 100, 1) if total > 0 else 0
        return {"total": total, "up": up, "down": down, "pct_positive": pct_positive}
    finally:
        conn.close()


# init_db() est appelé explicitement au démarrage de l'application (api.py lifespan)
# et ne doit PAS être exécuté à l'import pour éviter des connexions réseau non désirées
# (tests, CI/CD sans DATABASE_URL, imports isolés).
