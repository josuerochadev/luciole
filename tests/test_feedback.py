"""
Tests pour le feedback sur les réponses (Phase 6).
- database.py : save_response_feedback, get_response_feedback_stats
- api.py : POST /feedback/response, GET /feedback/stats
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conv_db(tmp_path, monkeypatch):
    """Module database.py pointant vers une DB temporaire."""
    import database as db_mod
    db_path = str(tmp_path / "test_luciole.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_mod


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Client TestClient FastAPI avec DB temporaire + utilisateur authentifié."""
    import database as db_mod
    db_path = str(tmp_path / "test_luciole.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")

    import auth
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret-key")

    from fastapi.testclient import TestClient
    from api import app

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
# Tests database.py — save_response_feedback / get_response_feedback_stats
# ---------------------------------------------------------------------------

class TestFeedbackDatabase:
    def test_save_feedback_up(self, conv_db):
        conv = conv_db.create_conversation("Test")
        msg = conv_db.add_message(conv["id"], "assistant", "Réponse")
        fb = conv_db.save_response_feedback(msg["id"], "up")
        assert fb["message_id"] == msg["id"]
        assert fb["rating"] == "up"
        assert fb["comment"] is None

    def test_save_feedback_down_with_comment(self, conv_db):
        conv = conv_db.create_conversation("Test")
        msg = conv_db.add_message(conv["id"], "assistant", "Réponse")
        fb = conv_db.save_response_feedback(msg["id"], "down", "Pas pertinent")
        assert fb["rating"] == "down"
        assert fb["comment"] == "Pas pertinent"

    def test_save_feedback_upsert(self, conv_db):
        """Le feedback est remplacé (pas dupliqué) pour un même message."""
        conv = conv_db.create_conversation("Test")
        msg = conv_db.add_message(conv["id"], "assistant", "Réponse")
        conv_db.save_response_feedback(msg["id"], "up")
        conv_db.save_response_feedback(msg["id"], "down", "Changé d'avis")
        stats = conv_db.get_response_feedback_stats()
        assert stats["total"] == 1
        assert stats["down"] == 1
        assert stats["up"] == 0

    def test_feedback_stats_vide(self, conv_db):
        stats = conv_db.get_response_feedback_stats()
        assert stats["total"] == 0
        assert stats["pct_positive"] == 0

    def test_feedback_stats_calcul(self, conv_db):
        conv = conv_db.create_conversation("Test")
        for i in range(3):
            msg = conv_db.add_message(conv["id"], "assistant", f"Réponse {i}")
            rating = "up" if i < 2 else "down"
            conv_db.save_response_feedback(msg["id"], rating)
        stats = conv_db.get_response_feedback_stats()
        assert stats["total"] == 3
        assert stats["up"] == 2
        assert stats["down"] == 1
        assert stats["pct_positive"] == pytest.approx(66.7, abs=0.1)

    def test_save_feedback_invalid_rating(self, conv_db):
        """Un rating invalide doit lever une erreur SQLite CHECK."""
        import sqlite3
        conv = conv_db.create_conversation("Test")
        msg = conv_db.add_message(conv["id"], "assistant", "Réponse")
        with pytest.raises(sqlite3.IntegrityError):
            conv_db.save_response_feedback(msg["id"], "invalid")


# ---------------------------------------------------------------------------
# Tests endpoints API
# ---------------------------------------------------------------------------

class TestFeedbackAPI:
    def test_post_feedback_up(self, api_client, tmp_path, monkeypatch):
        import database as db_mod
        conv = db_mod.create_conversation("Test", user_id=None)
        msg = db_mod.add_message(conv["id"], "assistant", "Réponse")
        res = api_client.post("/feedback/response", json={
            "message_id": msg["id"],
            "rating": "up",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["rating"] == "up"
        assert data["message_id"] == msg["id"]

    def test_post_feedback_down_with_comment(self, api_client, tmp_path, monkeypatch):
        import database as db_mod
        conv = db_mod.create_conversation("Test")
        msg = db_mod.add_message(conv["id"], "assistant", "Réponse")
        res = api_client.post("/feedback/response", json={
            "message_id": msg["id"],
            "rating": "down",
            "comment": "Hors sujet",
        })
        assert res.status_code == 200
        assert res.json()["comment"] == "Hors sujet"

    def test_post_feedback_invalid_rating(self, api_client):
        res = api_client.post("/feedback/response", json={
            "message_id": "fake-id",
            "rating": "neutral",
        })
        assert res.status_code == 422

    def test_post_feedback_missing_fields(self, api_client):
        res = api_client.post("/feedback/response", json={})
        assert res.status_code == 422

    def test_get_feedback_stats(self, api_client, tmp_path, monkeypatch):
        import database as db_mod
        conv = db_mod.create_conversation("Test")
        msg1 = db_mod.add_message(conv["id"], "assistant", "R1")
        msg2 = db_mod.add_message(conv["id"], "assistant", "R2")
        db_mod.save_response_feedback(msg1["id"], "up")
        db_mod.save_response_feedback(msg2["id"], "down")

        res = api_client.get("/feedback/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["up"] == 1
        assert data["down"] == 1
        assert data["pct_positive"] == 50.0

    def test_get_feedback_stats_empty(self, api_client):
        res = api_client.get("/feedback/stats")
        assert res.status_code == 200
        assert res.json()["total"] == 0
