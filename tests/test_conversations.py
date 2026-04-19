"""
Tests pour l'historique des conversations (database.py + endpoints API).
"""
import pytest
import sqlite3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conv_db(tmp_path, monkeypatch):
    """Fournit un module database.py pointant vers une DB temporaire."""
    import database as db_mod
    db_path = str(tmp_path / "test_luciole.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_mod


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Client TestClient FastAPI avec DB temporaire + utilisateur authentifié."""
    # Patch database.py avant import api
    import database as db_mod
    db_path = str(tmp_path / "test_luciole.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    # Patch API key + JWT secret
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")

    # Patch auth JWT_SECRET (already loaded at import time)
    import auth
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret-key")

    from fastapi.testclient import TestClient
    from api import app

    # Create a test user and get a JWT cookie
    user = db_mod.create_user(
        email="test@example.com",
        password_hash=auth.hash_password("password123"),
        display_name="Testeur",
    )
    token = auth.create_access_token(user["id"])

    client = TestClient(app)
    client.cookies.set(auth.COOKIE_NAME, token)
    return client


# ---------------------------------------------------------------------------
# Tests CRUD database.py
# ---------------------------------------------------------------------------

class TestDatabaseCRUD:
    def test_create_conversation(self, conv_db):
        conv = conv_db.create_conversation("Mon titre")
        assert conv["id"]
        assert conv["title"] == "Mon titre"
        assert conv["created_at"]

    def test_create_conversation_sans_titre(self, conv_db):
        conv = conv_db.create_conversation()
        assert conv["title"] is None

    def test_list_conversations_vide(self, conv_db):
        result = conv_db.list_conversations()
        assert result == []

    def test_list_conversations_ordre(self, conv_db):
        c1 = conv_db.create_conversation("Première")
        c2 = conv_db.create_conversation("Deuxième")
        # c2 créée après c1, donc c2 en premier (DESC)
        result = conv_db.list_conversations()
        assert len(result) == 2
        assert result[0]["id"] == c2["id"]

    def test_get_conversation(self, conv_db):
        conv = conv_db.create_conversation("Test")
        result = conv_db.get_conversation(conv["id"])
        assert result["title"] == "Test"

    def test_get_conversation_inexistante(self, conv_db):
        result = conv_db.get_conversation("id-bidon")
        assert result is None

    def test_add_message(self, conv_db):
        conv = conv_db.create_conversation("Test")
        msg = conv_db.add_message(conv["id"], "user", "Bonjour")
        assert msg["role"] == "user"
        assert msg["content"] == "Bonjour"
        assert msg["conversation_id"] == conv["id"]

    def test_get_conversation_messages(self, conv_db):
        conv = conv_db.create_conversation("Test")
        conv_db.add_message(conv["id"], "user", "Question")
        conv_db.add_message(conv["id"], "assistant", "Réponse")
        msgs = conv_db.get_conversation_messages(conv["id"])
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_get_conversation_messages_ordre_chrono(self, conv_db):
        conv = conv_db.create_conversation("Test")
        conv_db.add_message(conv["id"], "user", "Premier")
        conv_db.add_message(conv["id"], "user", "Deuxième")
        conv_db.add_message(conv["id"], "user", "Troisième")
        msgs = conv_db.get_conversation_messages(conv["id"])
        assert msgs[0]["content"] == "Premier"
        assert msgs[2]["content"] == "Troisième"

    def test_delete_conversation(self, conv_db):
        conv = conv_db.create_conversation("Test")
        conv_db.add_message(conv["id"], "user", "Msg")
        assert conv_db.delete_conversation(conv["id"]) is True
        assert conv_db.get_conversation(conv["id"]) is None
        assert conv_db.get_conversation_messages(conv["id"]) == []

    def test_delete_conversation_inexistante(self, conv_db):
        assert conv_db.delete_conversation("id-bidon") is False

    def test_update_conversation_title(self, conv_db):
        conv = conv_db.create_conversation("Ancien")
        assert conv_db.update_conversation_title(conv["id"], "Nouveau") is True
        result = conv_db.get_conversation(conv["id"])
        assert result["title"] == "Nouveau"

    def test_update_conversation_title_inexistante(self, conv_db):
        assert conv_db.update_conversation_title("id-bidon", "Titre") is False

    def test_get_recent_messages(self, conv_db):
        conv = conv_db.create_conversation("Test")
        for i in range(10):
            conv_db.add_message(conv["id"], "user", f"Msg {i}")
        recent = conv_db.get_recent_messages(conv["id"], n=3)
        assert len(recent) == 3
        # Les 3 derniers, dans l'ordre chronologique
        assert recent[0]["content"] == "Msg 7"
        assert recent[2]["content"] == "Msg 9"

    def test_add_message_met_a_jour_updated_at(self, conv_db):
        conv = conv_db.create_conversation("Test")
        before = conv_db.get_conversation(conv["id"])["updated_at"]
        conv_db.add_message(conv["id"], "user", "Msg")
        after = conv_db.get_conversation(conv["id"])["updated_at"]
        assert after >= before

    def test_cascade_on_delete(self, conv_db):
        """Vérifie que les messages sont supprimés avec la conversation (FK CASCADE)."""
        conv = conv_db.create_conversation("Test")
        conv_db.add_message(conv["id"], "user", "Msg1")
        conv_db.add_message(conv["id"], "assistant", "Msg2")
        conv_db.delete_conversation(conv["id"])
        # Vérification directe en DB
        conn = sqlite3.connect(conv_db.DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv["id"],)
        ).fetchone()[0]
        conn.close()
        assert count == 0


# ---------------------------------------------------------------------------
# Tests endpoints API
# ---------------------------------------------------------------------------

class TestConversationsAPI:
    def test_list_conversations_vide(self, api_client):
        res = api_client.get("/conversations")
        assert res.status_code == 200
        assert res.json() == []

    def test_get_messages_404(self, api_client):
        res = api_client.get("/conversations/id-bidon/messages")
        assert res.status_code == 404

    def test_delete_conversation_404(self, api_client):
        res = api_client.delete("/conversations/id-bidon")
        assert res.status_code == 404

    def test_patch_conversation_404(self, api_client):
        res = api_client.patch(
            "/conversations/id-bidon",
            json={"title": "Nouveau"},
        )
        assert res.status_code == 404

    def test_patch_conversation_validation(self, api_client):
        res = api_client.patch(
            "/conversations/id-bidon",
            json={"title": ""},
        )
        assert res.status_code == 422  # validation error (min_length=1)
