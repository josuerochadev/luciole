"""
Tests — Phase 5 : Dark mode.
Vérifie que le toggle theme et les assets dark mode sont bien intégrés
sur toutes les pages publiques.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api import app

client = TestClient(app, cookies={})


# ── Pages à tester (toutes héritent de base.html) ──────────────

PAGES = [
    ("/", 200, "chat"),
    ("/about", 200, "about"),
    ("/dashboard", 200, "dashboard"),
    ("/digest-page", 200, "digest"),
    ("/login", 200, "login"),
]


@pytest.fixture
def auth_client():
    """Client authentifié pour les pages protégées."""
    c = TestClient(app)
    # Créer un compte et se connecter
    c.post("/auth/register", data={
        "email": "darkmode@test.com",
        "password": "TestPass123!",
        "display_name": "DarkTest",
    })
    c.post("/auth/login", data={
        "email": "darkmode@test.com",
        "password": "TestPass123!",
    })
    return c


# ── 1. Bouton toggle présent sur chaque page ─────────────────

@pytest.mark.parametrize("path,expected_status,label", PAGES)
def test_toggle_button_present(path, expected_status, label):
    """Le bouton theme-toggle est dans le HTML de chaque page."""
    r = client.get(path, follow_redirects=True)
    assert r.status_code == 200
    assert 'id="theme-toggle"' in r.text, f"Bouton toggle absent sur {path}"


@pytest.mark.parametrize("path,expected_status,label", PAGES)
def test_toggle_has_aria_label(path, expected_status, label):
    """Le bouton toggle a un aria-label pour l'accessibilité."""
    r = client.get(path, follow_redirects=True)
    assert 'aria-label="Basculer le mode sombre"' in r.text, (
        f"aria-label manquant sur le toggle de {path}"
    )


# ── 2. Script d'initialisation dans le <head> ────────────────

@pytest.mark.parametrize("path,expected_status,label", PAGES)
def test_theme_init_script_in_head(path, expected_status, label):
    """Le script de pré-initialisation du thème est dans le <head>."""
    r = client.get(path, follow_redirects=True)
    html = r.text
    head_end = html.find("</head>")
    head_section = html[:head_end]
    assert "luciole-theme" in head_section, (
        f"Script init theme absent du <head> sur {path}"
    )


# ── 3. Script toggle (logique JS) ────────────────────────────

@pytest.mark.parametrize("path,expected_status,label", PAGES)
def test_theme_toggle_script(path, expected_status, label):
    """La logique JS du toggle (localStorage + data-theme) est présente."""
    r = client.get(path, follow_redirects=True)
    assert "localStorage.setItem" in r.text and "data-theme" in r.text, (
        f"Logique toggle JS absente sur {path}"
    )


# ── 4. CSS dark mode servi ────────────────────────────────────

def test_css_contains_dark_mode_variables():
    """Le CSS contient les overrides dark mode."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    assert r.status_code == 200
    css = r.text
    assert "prefers-color-scheme: dark" in css, "Media query dark absente du CSS"
    assert '[data-theme="dark"]' in css, "Sélecteur data-theme=dark absent du CSS"


def test_css_dark_mode_ink_value():
    """La variable --luciole-ink est bien redéfinie en dark mode."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    css = r.text
    # Vérifier que la valeur dark ink (#e8e8e8) apparaît
    assert "#e8e8e8" in css, "Couleur ink dark (#e8e8e8) absente"


def test_css_dark_mode_paper_value():
    """La variable --luciole-paper est bien redéfinie en dark mode."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    css = r.text
    assert "#1a1a1a" in css, "Couleur paper dark (#1a1a1a) absente"


def test_css_dark_mode_accent_value():
    """L'accent dark (#ef4444) est plus clair pour le contraste."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    css = r.text
    assert "#ef4444" in css, "Couleur accent dark (#ef4444) absente"


def test_css_theme_toggle_style():
    """Le style du bouton .luciole-theme-toggle est défini."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    assert ".luciole-theme-toggle" in r.text, "Style toggle absent du CSS"


# ── 5. Icône soleil/lune ──────────────────────────────────────

def test_theme_icon_element():
    """L'élément theme-icon est présent (pour basculer soleil/lune)."""
    r = client.get("/", follow_redirects=True)
    assert 'id="theme-icon"' in r.text, "Élément theme-icon absent"
