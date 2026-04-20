"""
Persistance SQLite pour l'historique des conversations.
Tables : conversations, messages.
Fichier : data/luciole.db
"""
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DATA_DIR

DB_PATH = f"{DATA_DIR}/luciole.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = _get_connection()
    try:
        # Create tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                user_id TEXT REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens_used INTEGER,
                latency_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id);

            CREATE TABLE IF NOT EXISTS response_feedback (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                rating TEXT NOT NULL CHECK(rating IN ('up', 'down')),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_response_feedback_msg
                ON response_feedback(message_id);
        """)

        # Migration: add user_id column if missing (existing databases)
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        if "user_id" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT REFERENCES users(id)")

        # Index on user_id (after migration to ensure column exists)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
        conn.commit()
    finally:
        conn.close()


def create_user(email: str, password_hash: str, display_name: str | None = None) -> dict:
    """Crée un nouvel utilisateur."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
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
        row = conn.execute(
            "SELECT id, email, password_hash, display_name, created_at FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    """Retourne un utilisateur par son ID, ou None."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_conversation(title: str | None = None, user_id: str | None = None) -> dict:
    """Crée une nouvelle conversation et retourne ses métadonnées."""
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (id, title, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
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
        if user_id:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id IS NULL ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_conversation(conv_id: str) -> dict | None:
    """Retourne une conversation par son ID, ou None."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_conversation_messages(conv_id: str) -> list[dict]:
    """Retourne tous les messages d'une conversation (ordre chronologique)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT id, role, content, tokens_used, latency_ms, created_at "
            "FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conv_id,),
        ).fetchall()
        return [dict(r) for r in rows]
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
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, tokens_used, latency_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, conv_id, role, content, tokens_used, latency_ms, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
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
        cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_conversation_title(conv_id: str, title: str) -> bool:
    """Met à jour le titre d'une conversation. Retourne True si elle existait."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conv_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_recent_messages(conv_id: str, n: int = 20) -> list[dict]:
    """Retourne les N derniers messages d'une conversation (pour le contexte LLM)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (conv_id, n),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()


def save_response_feedback(message_id: str, rating: str, comment: str | None = None) -> dict:
    """Sauvegarde un feedback sur une réponse (up/down)."""
    fb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        # Upsert: remplace le feedback existant pour ce message
        conn.execute(
            "DELETE FROM response_feedback WHERE message_id = ?",
            (message_id,),
        )
        conn.execute(
            "INSERT INTO response_feedback (id, message_id, rating, comment, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
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
        total = conn.execute("SELECT COUNT(*) as c FROM response_feedback").fetchone()["c"]
        up = conn.execute("SELECT COUNT(*) as c FROM response_feedback WHERE rating = 'up'").fetchone()["c"]
        down = conn.execute("SELECT COUNT(*) as c FROM response_feedback WHERE rating = 'down'").fetchone()["c"]
        pct_positive = round((up / total) * 100, 1) if total > 0 else 0
        return {"total": total, "up": up, "down": down, "pct_positive": pct_positive}
    finally:
        conn.close()


# Init au chargement du module
init_db()
