"""
Tests — Audit UX 6 : corrections critiques accessibilité & interactions.
Vérifie les 7 problèmes critiques : CSS syntax, headings, ARIA tabs,
role=alert, sidebar delete keyboard, Plotly dark mode, inline API key.

Lancer : pytest tests/test_ux_critiques.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


# ── 1. Hiérarchie de headings ──────────────────────────────────────────────


def test_dashboard_has_h1():
    """La page /dashboard a un <h1> (hiérarchie heading WCAG 1.3.1)."""
    r = client.get("/dashboard", follow_redirects=True)
    assert r.status_code == 200
    assert "<h1" in r.text, "Aucun <h1> sur /dashboard"


def test_digest_has_h1():
    """La page /digest-page a un <h1> (hiérarchie heading WCAG 1.3.1)."""
    r = client.get("/digest-page", follow_redirects=True)
    assert r.status_code == 200
    assert "<h1" in r.text, "Aucun <h1> sur /digest-page"


def test_digest_has_h2_sections():
    """Les sections du digest utilisent <h2> (via redirect login si non authentifié)."""
    r = client.get("/digest-page", follow_redirects=True)
    assert r.status_code == 200
    assert "<h2" in r.text, "Aucun <h2> dans la réponse /digest-page"


def test_dashboard_has_h2_sections():
    """Les sections du dashboard utilisent <h2> (généré par JS)."""
    r = client.get("/dashboard", follow_redirects=True)
    # Les h2 sont dans les template strings JS du dashboard
    assert (
        "'<h2 class=\"dash-section\">" in r.text
        or '"<h2 class=\\"dash-section\\">' in r.text
        or "<h2 class" in r.text
    ), "Aucun <h2> de section dans /dashboard"


# ── 2. Auth tabs — ARIA pattern ────────────────────────────────────────────


def test_login_tabs_have_tablist_role():
    """Le conteneur d'onglets a role='tablist' (WCAG 4.1.2)."""
    r = client.get("/login", follow_redirects=True)
    assert 'role="tablist"' in r.text, "role='tablist' absent sur /login"


def test_login_tabs_have_tab_role():
    """Les boutons d'onglets ont role='tab' (WCAG 4.1.2)."""
    r = client.get("/login", follow_redirects=True)
    assert 'role="tab"' in r.text, "role='tab' absent sur /login"


def test_login_tabs_have_aria_selected():
    """L'onglet actif a aria-selected='true' (WCAG 4.1.2)."""
    r = client.get("/login", follow_redirects=True)
    assert 'aria-selected="true"' in r.text, "aria-selected='true' absent sur /login"


def test_login_tabs_have_aria_controls():
    """Les onglets référencent leurs panneaux via aria-controls."""
    r = client.get("/login", follow_redirects=True)
    assert 'aria-controls="login-form"' in r.text, "aria-controls='login-form' absent"
    assert 'aria-controls="register-form"' in r.text, "aria-controls='register-form' absent"


def test_login_panels_have_tabpanel_role():
    """Les formulaires ont role='tabpanel' (WCAG 4.1.2)."""
    r = client.get("/login", follow_redirects=True)
    assert 'role="tabpanel"' in r.text, "role='tabpanel' absent sur /login"


# ── 3. role="alert" sur les erreurs de formulaire ─────────────────────────


def test_login_error_divs_have_role_alert():
    """Les deux divs d'erreur ont role='alert' (WCAG 4.1.3)."""
    r = client.get("/login", follow_redirects=True)
    count = r.text.count('role="alert"')
    assert count >= 2, f"Attendu au moins 2 role='alert' sur /login, trouvé {count}"


# ── 4. CSS syntax — dragover dark mode ────────────────────────────────────


def test_css_dragover_invalid_comma_syntax_absent():
    """La syntaxe CSS invalide (sélecteur+virgule+@media) est corrigée."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    css = r.text
    assert "luciole-dragover::after,\n@media" not in css and "luciole-dragover::after,\r\n@media" not in css, (
        "Syntaxe CSS invalide (comma+@media) encore présente dans luciole.css"
    )


def test_css_dragover_data_theme_dark_rule_exists():
    """La règle dark dragover pour [data-theme='dark'] est correctement définie."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    assert '[data-theme="dark"] .luciole-dragover::after' in r.text, (
        "Règle [data-theme=dark] .luciole-dragover::after manquante"
    )


# ── 5. Sidebar delete — accessible au clavier ─────────────────────────────


def test_css_sidebar_delete_focus_visible():
    """Le CSS rend .luciole-sidebar-delete visible au focus clavier."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    assert ".luciole-sidebar-delete:focus-visible" in r.text, (
        "Règle :focus-visible manquante pour .luciole-sidebar-delete"
    )


def test_js_sidebar_delete_is_button():
    """Le JS génère un <button> pour l'action de suppression (pas un <span>)."""
    r = client.get("/static/luciole-chat.js", params={"v": "test"})
    assert '<button class="luciole-sidebar-delete"' in r.text, (
        "Le bouton delete n'est pas un <button> dans luciole-chat.js"
    )


# ── 6. Digest — champ API key inline (pas de prompt()) ────────────────────


def test_digest_has_apikey_input():
    """La page digest a un input#apikey-input pour la clé API."""
    r = client.get("/digest-page", follow_redirects=True)
    assert 'id="apikey-input"' in r.text, (
        "Champ #apikey-input absent sur /digest-page"
    )


def test_digest_no_window_prompt():
    """La page digest ne contient plus d'appel à prompt()."""
    r = client.get("/digest-page", follow_redirects=True)
    html = r.text
    assert "= prompt(" not in html and "window.prompt" not in html, (
        "window.prompt() encore présent sur /digest-page"
    )


# ── 7. Plotly — couleurs dynamiques depuis CSS vars ───────────────────────


def test_dashboard_plotly_reads_css_vars():
    """Le dashboard lit les couleurs CSS via getComputedStyle (pas hard-codées)."""
    r = client.get("/dashboard", follow_redirects=True)
    assert "getComputedStyle" in r.text, (
        "getComputedStyle absent — couleurs Plotly probablement encore hard-codées"
    )


def test_dashboard_no_hardcoded_plotly_paper_color():
    """Le layout Plotly ne contient plus paper_bgcolor: '#faf8f3' hard-codé."""
    r = client.get("/dashboard", follow_redirects=True)
    assert "paper_bgcolor: '#faf8f3'" not in r.text, (
        "Couleur paper hard-codée #faf8f3 encore dans le layout Plotly"
    )
