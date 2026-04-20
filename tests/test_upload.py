"""
Tests pour le système d'upload de fichiers (Phase 4).
- Unitaires : validation magic bytes, nettoyage fichiers expirés
- Intégration : endpoint POST /upload, POST /ask avec file_id
"""
import io
import os
import time
import struct

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def upload_dir(tmp_path):
    """Répertoire d'upload temporaire."""
    d = tmp_path / "uploads"
    d.mkdir()
    return d


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient FastAPI avec un utilisateur authentifié."""
    import database as db_mod
    db_path = str(tmp_path / "test_upload.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")

    import auth
    monkeypatch.setattr(auth, "JWT_SECRET", "test-jwt-secret")

    # Patcher UPLOAD_DIR vers un répertoire temporaire
    import config
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(config, "UPLOAD_DIR", str(upload_dir))

    # Patcher aussi dans api.py (importé au top-level)
    import api as api_mod
    monkeypatch.setattr(api_mod, "UPLOAD_DIR", str(upload_dir))

    from fastapi.testclient import TestClient
    from api import app, limiter
    limiter.enabled = False

    c = TestClient(app)

    # Enregistrer un utilisateur et récupérer le cookie
    res = c.post("/auth/register", json={
        "email": "uploader@test.com",
        "password": "password123",
        "display_name": "Uploader",
    })
    assert res.status_code == 200
    c.cookies.set("access_token", res.cookies["access_token"])

    yield c, upload_dir

    limiter.enabled = True


@pytest.fixture
def unauth_client(tmp_path, monkeypatch):
    """TestClient FastAPI sans authentification."""
    import database as db_mod
    db_path = str(tmp_path / "test_upload_unauth.db")
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")

    import auth
    monkeypatch.setattr(auth, "JWT_SECRET", "test-jwt-secret")

    import config
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(config, "UPLOAD_DIR", str(upload_dir))

    import api as api_mod
    monkeypatch.setattr(api_mod, "UPLOAD_DIR", str(upload_dir))

    from fastapi.testclient import TestClient
    from api import app, limiter
    limiter.enabled = False

    c = TestClient(app)
    yield c

    limiter.enabled = True


# ---------------------------------------------------------------------------
# Helpers — Fichiers factices avec magic bytes valides
# ---------------------------------------------------------------------------

def make_png(size=100):
    """Crée un fichier PNG minimal valide."""
    # PNG signature + IHDR chunk minimal
    sig = b"\x89PNG\r\n\x1a\n"
    # Minimal IHDR: 13 bytes (width=1, height=1, bit_depth=8, color_type=2)
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = b"\x00" * 4  # Fake CRC (not validated by our code)
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + ihdr_crc
    # Pad to desired size
    content = sig + ihdr
    if len(content) < size:
        content += b"\x00" * (size - len(content))
    return content


def make_jpeg(size=100):
    """Crée un fichier JPEG minimal valide."""
    content = b"\xff\xd8\xff\xe0" + b"\x00" * max(0, size - 4)
    return content


def make_pdf(size=100):
    """Crée un fichier PDF minimal valide."""
    content = b"%PDF-1.4 test" + b"\x00" * max(0, size - 13)
    return content


def make_mp3(size=100):
    """Crée un fichier MP3 minimal valide (ID3 tag)."""
    content = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * max(0, size - 10)
    return content


def make_wav(size=100):
    """Crée un fichier WAV minimal valide."""
    # RIFF....WAVE
    file_size = max(size - 8, 4)
    content = b"RIFF" + struct.pack("<I", file_size) + b"WAVE" + b"\x00" * max(0, size - 12)
    return content


def make_m4a(size=100):
    """Crée un fichier M4A minimal valide (ftyp box)."""
    # size(4) + "ftyp" + brand
    content = struct.pack(">I", 20) + b"ftyp" + b"M4A " + b"\x00" * max(0, size - 12)
    return content


def make_webp(size=100):
    """Crée un fichier WebP minimal valide."""
    file_size = max(size - 8, 4)
    content = b"RIFF" + struct.pack("<I", file_size) + b"WEBP" + b"\x00" * max(0, size - 12)
    return content


# ---------------------------------------------------------------------------
# Unitaires — Validation magic bytes
# ---------------------------------------------------------------------------

class TestMagicBytesValidation:
    def test_valid_png(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_png(), "image/png") is True

    def test_valid_jpeg(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_jpeg(), "image/jpeg") is True

    def test_valid_pdf(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_pdf(), "application/pdf") is True

    def test_valid_mp3(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_mp3(), "audio/mpeg") is True

    def test_valid_wav(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_wav(), "audio/wav") is True

    def test_valid_m4a(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_m4a(), "audio/mp4") is True

    def test_valid_webp(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_webp(), "image/webp") is True

    def test_invalid_png_wrong_bytes(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(b"NOT A PNG FILE", "image/png") is False

    def test_invalid_jpeg_wrong_bytes(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(b"NOT A JPEG", "image/jpeg") is False

    def test_invalid_type_mismatch(self):
        """Envoyer un vrai PNG mais déclarer audio/mpeg."""
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(make_png(), "audio/mpeg") is False

    def test_unknown_type_returns_false(self):
        from api import _validate_magic_bytes
        assert _validate_magic_bytes(b"whatever", "text/plain") is False


# ---------------------------------------------------------------------------
# Unitaires — Nettoyage fichiers expirés
# ---------------------------------------------------------------------------

class TestCleanupExpired:
    def test_cleanup_removes_old_files(self, upload_dir, monkeypatch):
        import config
        monkeypatch.setattr(config, "UPLOAD_DIR", str(upload_dir))

        # Importer après le monkeypatch
        import api as api_mod
        monkeypatch.setattr(api_mod, "UPLOAD_DIR", str(upload_dir))

        # Créer un fichier "expiré" (mtime il y a 2h)
        old_file = upload_dir / "old_file.png"
        old_file.write_bytes(b"old data")
        old_time = time.time() - 7200  # 2h ago
        os.utime(old_file, (old_time, old_time))

        # Créer un fichier "récent"
        new_file = upload_dir / "new_file.png"
        new_file.write_bytes(b"new data")

        from api import _cleanup_expired_uploads
        _cleanup_expired_uploads()

        assert not old_file.exists(), "Le fichier expiré devrait être supprimé"
        assert new_file.exists(), "Le fichier récent ne devrait pas être supprimé"

    def test_cleanup_empty_dir(self, upload_dir, monkeypatch):
        import config
        monkeypatch.setattr(config, "UPLOAD_DIR", str(upload_dir))
        import api as api_mod
        monkeypatch.setattr(api_mod, "UPLOAD_DIR", str(upload_dir))

        from api import _cleanup_expired_uploads
        # Should not raise
        _cleanup_expired_uploads()

    def test_cleanup_nonexistent_dir(self, tmp_path, monkeypatch):
        import config
        fake_dir = str(tmp_path / "nonexistent")
        monkeypatch.setattr(config, "UPLOAD_DIR", fake_dir)
        import api as api_mod
        monkeypatch.setattr(api_mod, "UPLOAD_DIR", fake_dir)

        from api import _cleanup_expired_uploads
        # Should not raise
        _cleanup_expired_uploads()


# ---------------------------------------------------------------------------
# Intégration — POST /upload
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    def test_upload_png_success(self, client):
        c, upload_dir = client
        data = make_png(500)
        res = c.post("/upload", files={"file": ("test.png", io.BytesIO(data), "image/png")})
        assert res.status_code == 200
        body = res.json()
        assert "file_id" in body
        assert body["filename"] == "test.png"
        assert body["type"] == "image/png"
        assert body["size"] == 500

        # Vérifier que le fichier existe sur disque
        saved = list(upload_dir.iterdir())
        assert len(saved) == 1
        assert saved[0].name.endswith(".png")

    def test_upload_jpeg_success(self, client):
        c, _ = client
        data = make_jpeg(300)
        res = c.post("/upload", files={"file": ("photo.jpg", io.BytesIO(data), "image/jpeg")})
        assert res.status_code == 200
        assert res.json()["type"] == "image/jpeg"

    def test_upload_pdf_success(self, client):
        c, _ = client
        data = make_pdf(200)
        res = c.post("/upload", files={"file": ("doc.pdf", io.BytesIO(data), "application/pdf")})
        assert res.status_code == 200
        assert res.json()["type"] == "application/pdf"

    def test_upload_mp3_success(self, client):
        c, _ = client
        data = make_mp3(400)
        res = c.post("/upload", files={"file": ("audio.mp3", io.BytesIO(data), "audio/mpeg")})
        assert res.status_code == 200
        assert res.json()["type"] == "audio/mpeg"

    def test_upload_wav_success(self, client):
        c, _ = client
        data = make_wav(500)
        res = c.post("/upload", files={"file": ("sound.wav", io.BytesIO(data), "audio/wav")})
        assert res.status_code == 200
        assert res.json()["type"] == "audio/wav"

    def test_upload_rejected_type(self, client):
        """Fichier avec type MIME non autorisé (text/plain)."""
        c, _ = client
        res = c.post("/upload", files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")})
        assert res.status_code == 400
        assert "non autorisé" in res.json()["detail"].lower() or "non autorise" in res.json()["detail"].lower()

    def test_upload_rejected_too_large(self, client, monkeypatch):
        """Fichier dépassant MAX_FILE_SIZE."""
        import config
        import api as api_mod
        # Temporairement réduire la limite à 100 octets
        monkeypatch.setattr(config, "MAX_FILE_SIZE", 100)
        monkeypatch.setattr(api_mod, "MAX_FILE_SIZE", 100)

        c, _ = client
        data = make_png(200)
        res = c.post("/upload", files={"file": ("big.png", io.BytesIO(data), "image/png")})
        assert res.status_code == 400
        assert "volumineux" in res.json()["detail"].lower()

    def test_upload_rejected_magic_bytes_mismatch(self, client):
        """Fichier déclaré PNG mais contenu texte."""
        c, _ = client
        res = c.post("/upload", files={"file": ("fake.png", io.BytesIO(b"not a png at all!!"), "image/png")})
        assert res.status_code == 400
        assert "correspond pas" in res.json()["detail"].lower()

    def test_upload_unique_filenames(self, client):
        """Deux uploads du même fichier donnent des file_id différents."""
        c, upload_dir = client
        data = make_png(100)
        res1 = c.post("/upload", files={"file": ("test.png", io.BytesIO(data), "image/png")})
        res2 = c.post("/upload", files={"file": ("test.png", io.BytesIO(data), "image/png")})
        assert res1.json()["file_id"] != res2.json()["file_id"]
        assert len(list(upload_dir.iterdir())) == 2

    def test_upload_requires_auth(self, unauth_client):
        """Upload sans authentification est refusé."""
        data = make_png(100)
        res = unauth_client.post("/upload", files={"file": ("test.png", io.BytesIO(data), "image/png")})
        # Soit 401, soit redirect vers login
        assert res.status_code in (401, 303)


# ---------------------------------------------------------------------------
# Intégration — POST /ask avec file_id
# ---------------------------------------------------------------------------

class TestAskWithFileId:
    def test_ask_with_invalid_file_id(self, client):
        """file_id inexistant retourne 404."""
        c, _ = client
        res = c.post("/ask", json={
            "question": "Analyse ce fichier",
            "file_id": "nonexistent123",
        })
        assert res.status_code == 404
        assert "introuvable" in res.json()["detail"].lower() or "expiré" in res.json()["detail"].lower()

    def test_ask_with_valid_file_id_image(self, client, monkeypatch):
        """Upload une image puis la passe à /ask — vérifie que l'agent reçoit le bon chemin."""
        c, upload_dir = client

        # Upload
        data = make_png(500)
        upload_res = c.post("/upload", files={"file": ("test.png", io.BytesIO(data), "image/png")})
        assert upload_res.status_code == 200
        file_id = upload_res.json()["file_id"]

        # Mock agent_react_stream pour capturer la question enrichie
        captured_questions = []

        async def fake_stream(question):
            captured_questions.append(question)
            yield {"type": "chunk", "content": "Réponse test"}
            yield {"type": "done", "latency_ms": 100, "full_response": "Réponse test"}

        monkeypatch.setattr("api.agent_react_stream", fake_stream)

        res = c.post("/ask", json={
            "question": "Que vois-tu sur cette image ?",
            "file_id": file_id,
        })
        assert res.status_code == 200

        # Vérifier que la question enrichie contient le chemin du fichier
        assert len(captured_questions) == 1
        q = captured_questions[0]
        assert file_id in q
        assert "image" in q.lower() or "analyse" in q.lower()

    def test_ask_with_valid_file_id_audio(self, client, monkeypatch):
        """Upload un audio puis le passe à /ask — vérifie le routing transcription."""
        c, upload_dir = client

        data = make_mp3(500)
        upload_res = c.post("/upload", files={"file": ("audio.mp3", io.BytesIO(data), "audio/mpeg")})
        assert upload_res.status_code == 200
        file_id = upload_res.json()["file_id"]

        captured_questions = []

        async def fake_stream(question):
            captured_questions.append(question)
            yield {"type": "chunk", "content": "Transcription test"}
            yield {"type": "done", "latency_ms": 100, "full_response": "Transcription test"}

        monkeypatch.setattr("api.agent_react_stream", fake_stream)

        res = c.post("/ask", json={
            "question": "Transcris ce fichier",
            "file_id": file_id,
        })
        assert res.status_code == 200

        assert len(captured_questions) == 1
        q = captured_questions[0]
        assert file_id in q
        assert "audio" in q.lower() or "transcri" in q.lower()

    def test_ask_with_valid_file_id_pdf(self, client, monkeypatch):
        """Upload un PDF puis le passe à /ask — vérifie le routing document."""
        c, upload_dir = client

        data = make_pdf(300)
        upload_res = c.post("/upload", files={"file": ("doc.pdf", io.BytesIO(data), "application/pdf")})
        assert upload_res.status_code == 200
        file_id = upload_res.json()["file_id"]

        captured_questions = []

        async def fake_stream(question):
            captured_questions.append(question)
            yield {"type": "chunk", "content": "Analyse PDF test"}
            yield {"type": "done", "latency_ms": 100, "full_response": "Analyse PDF test"}

        monkeypatch.setattr("api.agent_react_stream", fake_stream)

        res = c.post("/ask", json={
            "question": "Résume ce document",
            "file_id": file_id,
        })
        assert res.status_code == 200

        assert len(captured_questions) == 1
        q = captured_questions[0]
        assert file_id in q
        assert "pdf" in q.lower() or "document" in q.lower()

    def test_ask_without_file_id_works_normally(self, client, monkeypatch):
        """POST /ask sans file_id fonctionne comme avant."""
        c, _ = client

        captured = []

        async def fake_stream(question):
            captured.append(question)
            yield {"type": "chunk", "content": "Réponse normale"}
            yield {"type": "done", "latency_ms": 50, "full_response": "Réponse normale"}

        monkeypatch.setattr("api.agent_react_stream", fake_stream)

        res = c.post("/ask", json={"question": "Bonjour"})
        assert res.status_code == 200
        assert len(captured) == 1
        assert captured[0] == "Bonjour"


# ---------------------------------------------------------------------------
# Intégration — Config upload
# ---------------------------------------------------------------------------

class TestUploadConfig:
    def test_upload_dir_exists(self):
        from config import UPLOAD_DIR
        assert os.path.isdir(UPLOAD_DIR)

    def test_max_file_size_is_10mb(self):
        from config import MAX_FILE_SIZE
        assert MAX_FILE_SIZE == 10 * 1024 * 1024

    def test_allowed_types_count(self):
        from config import ALLOWED_TYPES
        assert len(ALLOWED_TYPES) == 7
        assert "image/png" in ALLOWED_TYPES
        assert "audio/mpeg" in ALLOWED_TYPES
        assert "application/pdf" in ALLOWED_TYPES

    def test_upload_ttl(self):
        from config import UPLOAD_TTL
        assert UPLOAD_TTL == 3600
