"""
Tests pour le système d'authentification (Phase 2).
- Unitaires : hash/verify password, create/decode JWT, CRUD users
- Intégration : endpoints /auth/register, /auth/login, /auth/logout, /auth/me
- Scoping : isolation des conversations par utilisateur
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_db(tmp_path, monkeypatch):
    """DB temporaire avec module database + auth patchés."""
    import database as db_mod
    db_path = str(tmp_path / "test_auth.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    import auth as auth_mod
    monkeypatch.setattr(auth_mod, "JWT_SECRET", "test-secret-for-auth")

    return db_mod, auth_mod


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient FastAPI sans cookie (visiteur non connecté)."""
    import database as db_mod
    db_path = str(tmp_path / "test_auth_api.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")

    import auth
    monkeypatch.setattr(auth, "JWT_SECRET", "test-jwt-secret")

    from fastapi.testclient import TestClient
    from api import app

    # Disable rate limiting for tests
    from api import limiter
    limiter.enabled = False

    client = TestClient(app)
    yield client

    limiter.enabled = True


# ---------------------------------------------------------------------------
# Unitaires — bcrypt
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_et_verify(self, auth_db):
        _, auth_mod = auth_db
        h = auth_mod.hash_password("monmotdepasse")
        assert h != "monmotdepasse"
        assert auth_mod.verify_password("monmotdepasse", h) is True

    def test_wrong_password(self, auth_db):
        _, auth_mod = auth_db
        h = auth_mod.hash_password("correct")
        assert auth_mod.verify_password("incorrect", h) is False

    def test_hash_unique(self, auth_db):
        _, auth_mod = auth_db
        h1 = auth_mod.hash_password("same")
        h2 = auth_mod.hash_password("same")
        assert h1 != h2  # bcrypt salt différent


# ---------------------------------------------------------------------------
# Unitaires — JWT
# ---------------------------------------------------------------------------

class TestJWT:
    def test_create_and_decode(self, auth_db):
        _, auth_mod = auth_db
        token = auth_mod.create_access_token("user-123")
        assert isinstance(token, str)
        uid = auth_mod.decode_token(token)
        assert uid == "user-123"

    def test_decode_invalid_token(self, auth_db):
        _, auth_mod = auth_db
        assert auth_mod.decode_token("n-importe-quoi") is None

    def test_decode_wrong_secret(self, auth_db):
        _, auth_mod = auth_db
        token = auth_mod.create_access_token("user-123")
        # Changer le secret
        auth_mod.JWT_SECRET = "autre-secret"
        assert auth_mod.decode_token(token) is None


# ---------------------------------------------------------------------------
# Unitaires — CRUD users (database.py)
# ---------------------------------------------------------------------------

class TestUsersCRUD:
    def test_create_user(self, auth_db):
        db_mod, auth_mod = auth_db
        user = db_mod.create_user("test@example.com", auth_mod.hash_password("pass123"), "Test User")
        assert user["id"]
        assert user["email"] == "test@example.com"
        assert user["display_name"] == "Test User"

    def test_get_user_by_email(self, auth_db):
        db_mod, auth_mod = auth_db
        db_mod.create_user("alice@test.fr", auth_mod.hash_password("pass"), "Alice")
        user = db_mod.get_user_by_email("alice@test.fr")
        assert user is not None
        assert user["display_name"] == "Alice"
        assert "password_hash" in user

    def test_get_user_by_email_case_insensitive(self, auth_db):
        db_mod, auth_mod = auth_db
        db_mod.create_user("Bob@Test.FR", auth_mod.hash_password("pass"), "Bob")
        user = db_mod.get_user_by_email("bob@test.fr")
        assert user is not None

    def test_get_user_by_email_not_found(self, auth_db):
        db_mod, _ = auth_db
        assert db_mod.get_user_by_email("inconnu@x.com") is None

    def test_get_user_by_id(self, auth_db):
        db_mod, auth_mod = auth_db
        created = db_mod.create_user("u@t.com", auth_mod.hash_password("p"))
        user = db_mod.get_user_by_id(created["id"])
        assert user is not None
        assert user["email"] == "u@t.com"
        # get_user_by_id ne retourne PAS le password_hash
        assert "password_hash" not in user

    def test_get_user_by_id_not_found(self, auth_db):
        db_mod, _ = auth_db
        assert db_mod.get_user_by_id("id-bidon") is None

    def test_duplicate_email_raises(self, auth_db):
        db_mod, auth_mod = auth_db
        db_mod.create_user("dup@test.com", auth_mod.hash_password("p"))
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            db_mod.create_user("dup@test.com", auth_mod.hash_password("p"))


# ---------------------------------------------------------------------------
# Intégration — Endpoints auth
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    def test_register_success(self, client):
        res = client.post("/auth/register", json={
            "email": "nouveau@test.com",
            "password": "password123",
            "display_name": "Nouveau",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["display_name"] == "Nouveau"
        # Cookie JWT set
        assert "access_token" in res.cookies

    def test_register_duplicate_email(self, client):
        client.post("/auth/register", json={
            "email": "dup@test.com",
            "password": "password123",
        })
        res = client.post("/auth/register", json={
            "email": "dup@test.com",
            "password": "autrepass",
        })
        assert res.status_code == 409

    def test_register_password_too_short(self, client):
        res = client.post("/auth/register", json={
            "email": "short@test.com",
            "password": "123",
        })
        assert res.status_code == 422

    def test_register_invalid_email(self, client):
        res = client.post("/auth/register", json={
            "email": "pas-un-email",
            "password": "password123",
        })
        assert res.status_code == 422

    def test_login_success(self, client):
        # Register first
        client.post("/auth/register", json={
            "email": "login@test.com",
            "password": "mypassword",
        })
        # Login
        res = client.post("/auth/login", json={
            "email": "login@test.com",
            "password": "mypassword",
        })
        assert res.status_code == 200
        assert res.json()["ok"] is True
        assert "access_token" in res.cookies

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={
            "email": "wrong@test.com",
            "password": "correct",
        })
        res = client.post("/auth/login", json={
            "email": "wrong@test.com",
            "password": "incorrect",
        })
        assert res.status_code == 401

    def test_login_unknown_email(self, client):
        res = client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "whatever",
        })
        assert res.status_code == 401

    def test_logout(self, client):
        res = client.post("/auth/logout")
        assert res.status_code == 200
        # Cookie should be cleared
        assert res.json()["ok"] is True

    def test_me_authenticated(self, client):
        # Register to get cookie
        res_reg = client.post("/auth/register", json={
            "email": "me@test.com",
            "password": "password123",
            "display_name": "Moi",
        })
        # Manually set the cookie from the register response
        client.cookies.set("access_token", res_reg.cookies["access_token"])
        res = client.get("/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "me@test.com"
        assert data["display_name"] == "Moi"

    def test_me_unauthenticated(self, client):
        res = client.get("/auth/me", headers={"accept": "application/json"})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Intégration — Protection des routes
# ---------------------------------------------------------------------------

class TestRouteProtection:
    def test_landing_redirects_when_not_logged_in(self, client):
        res = client.get("/", follow_redirects=False)
        assert res.status_code == 303
        assert "/login" in res.headers["location"]

    def test_about_accessible_without_login(self, client):
        res = client.get("/about")
        assert res.status_code == 200

    def test_conversations_401_when_not_logged_in(self, client):
        res = client.get("/conversations", headers={"accept": "application/json"})
        assert res.status_code == 401

    def test_login_page_accessible(self, client):
        res = client.get("/login")
        assert res.status_code == 200

    def test_login_page_redirects_if_logged_in(self, client):
        res_reg = client.post("/auth/register", json={
            "email": "redir@test.com",
            "password": "password123",
        })
        client.cookies.set("access_token", res_reg.cookies["access_token"])
        res = client.get("/login", follow_redirects=False)
        assert res.status_code == 303
        assert res.headers["location"] == "/"

    def test_health_public(self, client):
        res = client.get("/health")
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# Intégration — Isolation des conversations par utilisateur
# ---------------------------------------------------------------------------

class TestConversationScoping:
    def _register(self, client, email):
        """Register a user and return the client with cookie set."""
        res = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
        })
        assert res.status_code == 200
        return res.cookies

    def test_conversations_isolated_between_users(self, tmp_path, monkeypatch):
        """Chaque utilisateur ne voit que ses propres conversations."""
        import database as db_mod
        db_path = str(tmp_path / "test_scope.db")
        monkeypatch.setattr(db_mod, "DB_PATH", db_path)
        db_mod.init_db()

        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("JWT_SECRET", "test-jwt")

        import auth
        monkeypatch.setattr(auth, "JWT_SECRET", "test-jwt")

        from api import limiter
        limiter.enabled = False

        from fastapi.testclient import TestClient
        from api import app

        # Create users directly in DB (avoids rate limiter / cookie issues)
        user_a = db_mod.create_user("alice@test.com", auth.hash_password("pass123"), "Alice")
        user_b = db_mod.create_user("bob@test.com", auth.hash_password("pass123"), "Bob")

        # Create conversations
        db_mod.create_conversation("Conv Alice 1", user_id=user_a["id"])
        db_mod.create_conversation("Conv Alice 2", user_id=user_a["id"])
        db_mod.create_conversation("Conv Bob 1", user_id=user_b["id"])

        # User A sees only their conversations
        token_a = auth.create_access_token(user_a["id"])
        client_a = TestClient(app, cookies={auth.COOKIE_NAME: token_a})
        res = client_a.get("/conversations")
        assert res.status_code == 200
        convs_a = res.json()
        assert len(convs_a) == 2
        assert all("Alice" in c["title"] for c in convs_a)

        # User B sees only their conversations
        token_b = auth.create_access_token(user_b["id"])
        client_b = TestClient(app, cookies={auth.COOKIE_NAME: token_b})
        res = client_b.get("/conversations")
        assert res.status_code == 200
        convs_b = res.json()
        assert len(convs_b) == 1
        assert convs_b[0]["title"] == "Conv Bob 1"
