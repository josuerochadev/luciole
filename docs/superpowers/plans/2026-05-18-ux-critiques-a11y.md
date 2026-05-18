# UX Critiques — Accessibilité & Interactions (Audit 6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger les 7 problèmes critiques identifiés lors de l'audit UX 6 : syntaxe CSS invalide, hiérarchie de headings, accessibilité clavier, ARIA patterns, messages d'erreur, prompt() natif, et couleurs Plotly en dark mode.

**Architecture:** Toutes les corrections sont frontend-only (templates Jinja2, CSS, JS vanilla). Pas de changement de routing ni de modèles Python. Les tests utilisent FastAPI TestClient + assertions sur le HTML rendu, en suivant le pattern de `tests/test_darkmode.py`.

**Tech Stack:** Python 3.12, FastAPI TestClient, pytest, Jinja2 templates, CSS custom properties, Plotly 2.35, vanilla JS

---

## Fichiers modifiés

| Fichier | Raison |
|---------|--------|
| `tests/test_ux_critiques.py` | Créer — tests HTML structure (TDD) |
| `static/luciole.css` | Fix syntaxe CSS dragover dark + sidebar delete :focus-visible + `.luciole-sidebar-entry` |
| `static/luciole-chat.js` | Changer `<span>` delete → `<button>` dans le rendu sidebar |
| `templates/login.html` | ARIA tablist/tab/aria-selected + role="alert" sur erreurs |
| `templates/dashboard.html` | `<h1>`/`<h2>` semantiques + Plotly couleurs dynamiques via CSS vars |
| `templates/digest.html` | `<h1>`/`<h2>` semantiques + champ API key inline (remplacement prompt()) |

---

## Task 1 : Écrire les tests qui échouent

**Fichiers :**
- Créer : `tests/test_ux_critiques.py`

- [ ] **Step 1 : Créer le fichier de tests**

```python
"""
Tests — Audit UX 6 : corrections critiques accessibilité & interactions.
Vérifie les 7 problèmes critiques : CSS syntax, headings, ARIA tabs,
role=alert, sidebar delete keyboard, Plotly dark mode, inline API key.

Lancer : pytest tests/test_ux_critiques.py -v
"""
import sys
import os
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


def test_dashboard_has_h2_sections():
    """Les sections du dashboard utilisent <h2> (généré par JS)."""
    r = client.get("/dashboard", follow_redirects=True)
    # Les h2 sont dans les template strings JS du dashboard
    assert "'<h2 class=\"dash-section\">" in r.text or \
           '"<h2 class=\\"dash-section\\">' in r.text or \
           "<h2 class" in r.text, (
        "Aucun <h2> de section dans /dashboard"
    )


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
    assert 'aria-controls="login-form"' in r.text, \
        "aria-controls='login-form' absent"
    assert 'aria-controls="register-form"' in r.text, \
        "aria-controls='register-form' absent"


def test_login_panels_have_tabpanel_role():
    """Les formulaires ont role='tabpanel' (WCAG 4.1.2)."""
    r = client.get("/login", follow_redirects=True)
    assert 'role="tabpanel"' in r.text, "role='tabpanel' absent sur /login"


# ── 3. role="alert" sur les erreurs de formulaire ─────────────────────────

def test_login_error_divs_have_role_alert():
    """Les deux divs d'erreur ont role='alert' (WCAG 4.1.3)."""
    r = client.get("/login", follow_redirects=True)
    count = r.text.count('role="alert"')
    assert count >= 2, (
        f"Attendu au moins 2 role='alert' sur /login, trouvé {count}"
    )


# ── 4. CSS syntax — dragover dark mode ────────────────────────────────────

def test_css_dragover_invalid_comma_syntax_absent():
    """La syntaxe CSS invalide (sélecteur+virgule+@media) est corrigée."""
    r = client.get("/static/luciole.css", params={"v": "test"})
    css = r.text
    # L'ancienne syntaxe invalide était :
    # [data-theme="dark"] .luciole-dragover::after,
    # @media (prefers-color-scheme: dark) { ... }
    # Le marqueur de la syntaxe invalide est la présence de ::after,"
    # immédiatement avant un @media dans le même bloc
    assert 'luciole-dragover::after,\n@media' not in css and \
           'luciole-dragover::after,\r\n@media' not in css, (
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
```

- [ ] **Step 2 : Vérifier que tous les tests échouent**

```bash
cd /Users/josuexavierrocha/Projets/luciole
python -m pytest tests/test_ux_critiques.py -v 2>&1 | head -60
```

Attendu : tous les tests `FAILED` (certains peuvent passer si partiellement déjà corrigé).

- [ ] **Step 3 : Commit des tests**

```bash
git add tests/test_ux_critiques.py
git commit -m "test(a11y): ajout tests critiques audit UX 6 — tous en échec initial"
```

---

## Task 2 : Corriger la syntaxe CSS invalide (dragover dark mode)

**Fichiers :**
- Modifier : `static/luciole.css:110–115`

**Contexte :** La règle actuelle mélange un sélecteur CSS et une règle `@media` dans une liste comma-separated, ce qui est invalide. Le sélecteur `[data-theme="dark"] .luciole-dragover::after` est ignoré par les navigateurs.

- [ ] **Step 1 : Remplacer le bloc invalide (lignes 110–115)**

Localiser ce bloc dans `static/luciole.css` :

```css
/* Dark mode — Drag overlay fix */
[data-theme="dark"] .luciole-dragover::after,
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .luciole-dragover::after {
    background: rgba(26, 26, 26, 0.9);
  }
}
```

Le remplacer par :

```css
/* Dark mode — Drag overlay fix */
[data-theme="dark"] .luciole-dragover::after {
  background: rgba(26, 26, 26, 0.9);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .luciole-dragover::after {
    background: rgba(26, 26, 26, 0.9);
  }
}
```

- [ ] **Step 2 : Lancer les tests CSS**

```bash
python -m pytest tests/test_ux_critiques.py -v -k "dragover"
```

Attendu :
```
test_css_dragover_invalid_comma_syntax_absent PASSED
test_css_dragover_data_theme_dark_rule_exists PASSED
```

- [ ] **Step 3 : Commit**

```bash
git add static/luciole.css
git commit -m "fix(css): correction syntaxe invalide dark mode dragover overlay"
```

---

## Task 3 : Sidebar delete — accessible au clavier

**Fichiers :**
- Modifier : `static/luciole.css` (ajouter `.luciole-sidebar-entry` + `:focus-visible`)
- Modifier : `static/luciole-chat.js:131–144` (changer `<span>` en `<button>`, restructurer en `<div.luciole-sidebar-entry>`)

**Contexte :** Le bouton delete est actuellement un `<span>` imbriqué dans un `<button>`. Pour éviter l'imbrication invalide de `<button>` dans `<button>`, on structure chaque item comme `<div.luciole-sidebar-entry>` contenant deux `<button>` frères. Le delete est un `<button>` natif, accessible via Tab.

- [ ] **Step 1 : Ajouter les règles CSS pour `.luciole-sidebar-entry`**

Dans `static/luciole.css`, après la règle `.luciole-sidebar-item` (autour de la ligne 773), ajouter :

```css
/* Sidebar entry — conteneur flex pour item + delete */
.luciole-sidebar-entry {
  display: flex;
  align-items: stretch;
}

.luciole-sidebar-entry .luciole-sidebar-item {
  flex: 1;
  min-width: 0;
  width: auto;
}
```

Puis remplacer la règle hover existante (lignes 829–831) :

```css
/* AVANT — à remplacer */
.luciole-sidebar-item:hover .luciole-sidebar-delete {
  opacity: 1;
}
```

par :

```css
/* APRÈS */
.luciole-sidebar-entry:hover .luciole-sidebar-delete,
.luciole-sidebar-delete:focus-visible {
  opacity: 1;
}
```

- [ ] **Step 2 : Mettre à jour le rendu JS de la sidebar**

Dans `static/luciole-chat.js`, la fonction `renderSidebarList` génère les items autour de la ligne 131. Remplacer le `return` de la fonction map (lignes 135–144) :

```javascript
// AVANT
return (
  '<button class="luciole-sidebar-item' + (isActive ? ' active' : '') + '" data-id="' + conv.id + '">' +
    '<div class="luciole-sidebar-item-content">' +
      '<span class="luciole-sidebar-item-title">' + escapeHtml(title) + '</span>' +
      '<span class="luciole-sidebar-item-date">' + date + '</span>' +
    '</div>' +
    '<span class="luciole-sidebar-delete" data-id="' + conv.id + '" title="Supprimer">&times;</span>' +
  '</button>'
);
```

par :

```javascript
// APRÈS
return (
  '<div class="luciole-sidebar-entry">' +
    '<button class="luciole-sidebar-item' + (isActive ? ' active' : '') + '" data-id="' + conv.id + '">' +
      '<div class="luciole-sidebar-item-content">' +
        '<span class="luciole-sidebar-item-title">' + escapeHtml(title) + '</span>' +
        '<span class="luciole-sidebar-item-date">' + date + '</span>' +
      '</div>' +
    '</button>' +
    '<button class="luciole-sidebar-delete" type="button" data-id="' + conv.id + '" ' +
      'aria-label="Supprimer ' + escapeHtml(title) + '" title="Supprimer">&times;</button>' +
  '</div>'
);
```

- [ ] **Step 3 : Simplifier le handler click de `.luciole-sidebar-item`**

Toujours dans `luciole-chat.js`, le handler de click sur `.luciole-sidebar-item` (autour de la ligne 147) contient un guard inutile puisque le delete est maintenant un bouton frère. Remplacer :

```javascript
// AVANT
sidebarList.querySelectorAll('.luciole-sidebar-item').forEach(function (item) {
  item.addEventListener('click', function (e) {
    // Don't load conversation if clicking delete button
    if (e.target.classList.contains('luciole-sidebar-delete')) return;
    loadConversation(item.getAttribute('data-id'));
    // Close sidebar on mobile
    if (window.innerWidth <= 768) closeSidebar();
  });
});
```

par :

```javascript
// APRÈS
sidebarList.querySelectorAll('.luciole-sidebar-item').forEach(function (item) {
  item.addEventListener('click', function () {
    loadConversation(item.getAttribute('data-id'));
    if (window.innerWidth <= 768) closeSidebar();
  });
});
```

- [ ] **Step 4 : Lancer les tests sidebar**

```bash
python -m pytest tests/test_ux_critiques.py -v -k "sidebar"
```

Attendu :
```
test_css_sidebar_delete_focus_visible PASSED
test_js_sidebar_delete_is_button PASSED
```

- [ ] **Step 5 : Commit**

```bash
git add static/luciole.css static/luciole-chat.js
git commit -m "fix(a11y): sidebar delete accessible au clavier — button + focus-visible"
```

---

## Task 4 : Auth tabs — ARIA tablist pattern + role="alert"

**Fichiers :**
- Modifier : `templates/login.html:12–51` (HTML + JS)

**Contexte :** Les onglets Connexion/Inscription ne sont pas annoncés comme onglets par les lecteurs d'écran (manque `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`). Les messages d'erreur n'ont pas `role="alert"` donc ne sont pas lus automatiquement après soumission.

- [ ] **Step 1 : Mettre à jour le HTML des onglets (login.html:12–15)**

Remplacer :

```html
<!-- Tabs -->
<div class="luciole-auth-tabs">
  <button class="luciole-auth-tab active" data-tab="login">Connexion</button>
  <button class="luciole-auth-tab" data-tab="register">Inscription</button>
</div>
```

par :

```html
<!-- Tabs -->
<div class="luciole-auth-tabs" role="tablist" aria-label="Mode d'authentification">
  <button class="luciole-auth-tab active"
          role="tab"
          id="tab-login"
          aria-selected="true"
          aria-controls="login-form"
          data-tab="login">Connexion</button>
  <button class="luciole-auth-tab"
          role="tab"
          id="tab-register"
          aria-selected="false"
          aria-controls="register-form"
          data-tab="register">Inscription</button>
</div>
```

- [ ] **Step 2 : Ajouter role="tabpanel" aux formulaires (login.html:18, 34)**

Remplacer la ligne du formulaire de connexion :

```html
<!-- AVANT -->
<form class="luciole-auth-form" id="login-form">
```

par :

```html
<!-- APRÈS -->
<form class="luciole-auth-form" id="login-form" role="tabpanel" aria-labelledby="tab-login">
```

Et le formulaire d'inscription :

```html
<!-- AVANT -->
<form class="luciole-auth-form" id="register-form" hidden>
```

par :

```html
<!-- APRÈS -->
<form class="luciole-auth-form" id="register-form" role="tabpanel" aria-labelledby="tab-register" hidden>
```

- [ ] **Step 3 : Ajouter role="alert" aux divs d'erreur (login.html:27, 47)**

Remplacer :

```html
<div class="luciole-auth-error" id="login-error" hidden></div>
```

par :

```html
<div class="luciole-auth-error" id="login-error" role="alert" hidden></div>
```

Et :

```html
<div class="luciole-auth-error" id="register-error" hidden></div>
```

par :

```html
<div class="luciole-auth-error" id="register-error" role="alert" hidden></div>
```

- [ ] **Step 4 : Mettre à jour le JS des onglets (login.html:68–78)**

Remplacer le bloc `tabs.forEach` :

```javascript
// AVANT
tabs.forEach(function (tab) {
  tab.addEventListener('click', function () {
    tabs.forEach(function (t) { t.classList.remove('active'); });
    tab.classList.add('active');
    const target = tab.getAttribute('data-tab');
    loginForm.hidden = target !== 'login';
    registerForm.hidden = target !== 'register';
    loginError.hidden = true;
    registerError.hidden = true;
  });
});
```

par :

```javascript
// APRÈS
tabs.forEach(function (tab) {
  tab.addEventListener('click', function () {
    tabs.forEach(function (t) {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    const target = tab.getAttribute('data-tab');
    loginForm.hidden = target !== 'login';
    registerForm.hidden = target !== 'register';
    loginError.hidden = true;
    registerError.hidden = true;
  });
});

// Navigation clavier au sein du tablist (WCAG 2.1.1)
var tabContainer = document.querySelector('[role="tablist"]');
if (tabContainer) {
  tabContainer.addEventListener('keydown', function (e) {
    var tabsArr = Array.from(tabs);
    var idx = tabsArr.indexOf(document.activeElement);
    if (e.key === 'ArrowRight' && idx < tabsArr.length - 1) {
      e.preventDefault();
      tabsArr[idx + 1].focus();
      tabsArr[idx + 1].click();
    } else if (e.key === 'ArrowLeft' && idx > 0) {
      e.preventDefault();
      tabsArr[idx - 1].focus();
      tabsArr[idx - 1].click();
    }
  });
}
```

- [ ] **Step 5 : Lancer les tests auth**

```bash
python -m pytest tests/test_ux_critiques.py -v -k "login or alert"
```

Attendu :
```
test_login_tabs_have_tablist_role PASSED
test_login_tabs_have_tab_role PASSED
test_login_tabs_have_aria_selected PASSED
test_login_tabs_have_aria_controls PASSED
test_login_panels_have_tabpanel_role PASSED
test_login_error_divs_have_role_alert PASSED
```

- [ ] **Step 6 : Commit**

```bash
git add templates/login.html
git commit -m "fix(a11y): auth tabs — ARIA tablist/tab/aria-selected + role=alert sur erreurs"
```

---

## Task 5 : Hiérarchie de headings — dashboard et digest

**Fichiers :**
- Modifier : `templates/dashboard.html:207, 322, 339, 345` (HTML + JS template strings)
- Modifier : `templates/digest.html:173, 195, 211` (HTML statique)

**Contexte :** Les labels de section sont des `<div>`. Il faut les remplacer par des éléments heading sémantiques. Le CSS stylistique est appliqué sur la **classe**, pas sur le tag, donc la visuelle ne change pas.

- [ ] **Step 1 : Corriger le h1 statique du dashboard (dashboard.html:207)**

Remplacer :

```html
<div class="dash-section dash-section--accent">Tableau de bord · Monitoring</div>
```

par :

```html
<h1 class="dash-section dash-section--accent">Tableau de bord · Monitoring</h1>
```

- [ ] **Step 2 : Corriger les h2 dynamiques du dashboard (dashboard.html — template strings JS)**

Dans le bloc `// ── Build HTML ──` (autour de la ligne 319), remplacer :

```javascript
html += '<div class="dash-section">Performance</div>';
```

par :

```javascript
html += '<h2 class="dash-section">Performance</h2>';
```

Remplacer :

```javascript
html += '<div class="dash-section">Santé</div>';
```

par :

```javascript
html += '<h2 class="dash-section">Santé</h2>';
```

Remplacer :

```javascript
html += '<div class="dash-section">Requêtes récentes</div>';
```

par :

```javascript
html += '<h2 class="dash-section">Requêtes récentes</h2>';
```

Remplacer (la ligne pour le journal des requêtes, `dash-chart-label`) :

```javascript
html += '<div class="dash-chart-label">Journal des requêtes</div>';
```

par :

```javascript
html += '<h3 class="dash-chart-label">Journal des requêtes</h3>';
```

Et les deux chart labels :

```javascript
html += '<div class="dash-chart-label">Latence par requête (ms)</div>';
html += '<div class="dash-chart-label">Tokens par requête</div>';
```

par :

```javascript
html += '<h3 class="dash-chart-label">Latence par requête (ms)</h3>';
html += '<h3 class="dash-chart-label">Tokens par requête</h3>';
```

- [ ] **Step 3 : Corriger les headings statiques du digest (digest.html:173, 195, 211)**

Remplacer :

```html
<div class="digest-section digest-section--accent">Digest Email · Veille Technologique</div>
```

par :

```html
<h1 class="digest-section digest-section--accent">Digest Email · Veille Technologique</h1>
```

Remplacer :

```html
<div class="digest-section">Actions</div>
```

par :

```html
<h2 class="digest-section">Actions</h2>
```

Remplacer :

```html
<div class="digest-section">Historique des envois</div>
```

par :

```html
<h2 class="digest-section">Historique des envois</h2>
```

- [ ] **Step 4 : Lancer les tests headings**

```bash
python -m pytest tests/test_ux_critiques.py -v -k "h1 or h2"
```

Attendu :
```
test_dashboard_has_h1 PASSED
test_digest_has_h1 PASSED
test_dashboard_has_h2_sections PASSED
```

- [ ] **Step 5 : Commit**

```bash
git add templates/dashboard.html templates/digest.html
git commit -m "fix(a11y): hiérarchie heading h1/h2/h3 sur dashboard et digest"
```

---

## Task 6 : Digest — remplacer prompt() par un champ inline

**Fichiers :**
- Modifier : `templates/digest.html` (HTML + CSS + JS)

**Contexte :** `window.prompt()` est un dialog natif bloquant, non stylistique, qui expose un concept technique à l'utilisateur. On le remplace par un champ `<input type="password">` inline, dans la barre d'actions, stylé avec le design system existant.

- [ ] **Step 1 : Ajouter le CSS du champ API key dans le `<style>` du digest (digest.html, dans le bloc `<style>`)**

Ajouter à la fin du bloc `<style>` (avant `</style>`) :

```css
/* Champ clé API inline */
.digest-apikey-field {
  display: flex;
  align-items: center;
  gap: var(--luciole-space-2);
}

.digest-apikey-input {
  font-family: var(--luciole-sans);
  font-size: var(--luciole-text-sm);
  padding: var(--luciole-space-2) var(--luciole-space-3);
  border: 1px solid var(--luciole-rule);
  border-radius: 4px;
  background: var(--luciole-paper);
  color: var(--luciole-ink);
  outline: none;
  width: 200px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.digest-apikey-input:focus {
  border-color: var(--luciole-accent);
  box-shadow: 0 0 0 3px var(--luciole-accent-soft);
}

.digest-apikey-input::placeholder {
  color: var(--luciole-muted);
  font-style: italic;
}
```

- [ ] **Step 2 : Ajouter le champ dans le HTML de la barre d'actions (digest.html — div.digest-actions)**

Remplacer :

```html
<div class="digest-actions">
  <button class="digest-btn" id="btn-preview">Previsualiser</button>
  <button class="digest-btn digest-btn--accent" id="btn-send" disabled>Envoyer par email</button>
  <span class="digest-status" id="digest-status"></span>
</div>
```

par :

```html
<div class="digest-actions">
  <button class="digest-btn" id="btn-preview">Prévisualiser</button>
  <div class="digest-apikey-field">
    <label for="apikey-input" class="t-eyebrow">Clé API</label>
    <input type="password"
           id="apikey-input"
           class="digest-apikey-input"
           placeholder="X-API-Key"
           autocomplete="off"
           aria-label="Clé API pour l'envoi du digest">
  </div>
  <button class="digest-btn digest-btn--accent" id="btn-send" disabled>Envoyer par email</button>
  <span class="digest-status" id="digest-status"></span>
</div>
```

- [ ] **Step 3 : Mettre à jour le JS du bouton d'envoi**

Dans le bloc `btnSend.addEventListener` du JS inline (autour de la ligne 335), remplacer :

```javascript
// AVANT
btnSend.addEventListener('click', async function () {
  if (!confirm('Envoyer le digest par email aux destinataires configures ?')) return;

  btnSend.disabled = true;
  setStatus('Envoi en cours...', '');

  try {
    const apiKey = prompt('Cle API (X-API-Key) :', '');
    if (!apiKey) {
      setStatus('Envoi annule', '');
      btnSend.disabled = false;
      return;
    }
```

par :

```javascript
// APRÈS
btnSend.addEventListener('click', async function () {
  const apiKey = document.getElementById('apikey-input').value.trim();
  if (!apiKey) {
    setStatus('Saisissez la clé API avant d\'envoyer.', 'err');
    document.getElementById('apikey-input').focus();
    return;
  }

  if (!confirm('Envoyer le digest par email aux destinataires configurés ?')) return;

  btnSend.disabled = true;
  setStatus('Envoi en cours...', '');

  try {
```

- [ ] **Step 4 : Lancer les tests digest**

```bash
python -m pytest tests/test_ux_critiques.py -v -k "digest or prompt"
```

Attendu :
```
test_digest_has_apikey_input PASSED
test_digest_no_window_prompt PASSED
```

- [ ] **Step 5 : Commit**

```bash
git add templates/digest.html
git commit -m "fix(ux): remplacement prompt() par champ API key inline sur /digest-page"
```

---

## Task 7 : Plotly — couleurs dynamiques depuis CSS custom properties

**Fichiers :**
- Modifier : `templates/dashboard.html` (JS inline, autour des lignes 236–254 et 380–393)

**Contexte :** Le `plotlyLayout` hard-code des couleurs hexadécimales qui ne répondent pas aux CSS custom properties. En dark mode, les graphiques restent avec un fond clair. La solution : lire les CSS vars au runtime via `getComputedStyle`, et écouter les changements de thème via `MutationObserver`.

- [ ] **Step 1 : Remplacer le bloc `plotlyLayout` par une fonction `buildPlotlyLayout()`**

Remplacer le bloc actuel (lignes 236–253) :

```javascript
// ── Plotly editorial theme ──────────────────────────────
const plotlyLayout = {
  paper_bgcolor: '#faf8f3',
  plot_bgcolor: '#faf8f3',
  font: { family: 'Inter, sans-serif', size: 11, color: '#6b6b6b' },
  margin: { l: 40, r: 16, t: 10, b: 30 },
  xaxis: {
    gridcolor: '#d9d6d0', zerolinecolor: '#d9d6d0',
    showgrid: true, tickfont: { family: 'Inter', size: 10, color: '#6b6b6b' }
  },
  yaxis: {
    gridcolor: '#d9d6d0', zerolinecolor: '#d9d6d0',
    showgrid: true, tickfont: { family: 'Inter', size: 10, color: '#6b6b6b' }
  },
  hoverlabel: {
    bgcolor: '#ffffff', bordercolor: '#1a1a1a',
    font: { size: 11, family: 'JetBrains Mono, monospace' }
  }
};
const plotlyConfig = { displaylogo: false, displayModeBar: false };
```

par :

```javascript
// ── Plotly — couleurs depuis CSS custom properties ──────────
function getPlotlyColors() {
  var s = getComputedStyle(document.documentElement);
  return {
    paper:  s.getPropertyValue('--luciole-paper').trim()     || '#faf8f3',
    muted:  s.getPropertyValue('--luciole-muted').trim()     || '#6b6b6b',
    rule:   s.getPropertyValue('--luciole-rule').trim()      || '#d9d6d0',
    ink:    s.getPropertyValue('--luciole-ink').trim()       || '#1a1a1a',
    accent: s.getPropertyValue('--luciole-accent').trim()    || '#991b1b',
    white:  s.getPropertyValue('--luciole-white').trim()     || '#ffffff',
  };
}

function buildPlotlyLayout(extra) {
  var c = getPlotlyColors();
  return Object.assign({
    paper_bgcolor: c.paper,
    plot_bgcolor:  c.paper,
    font: { family: 'Inter, sans-serif', size: 11, color: c.muted },
    margin: { l: 40, r: 16, t: 10, b: 30 },
    xaxis: {
      gridcolor: c.rule, zerolinecolor: c.rule,
      showgrid: true, tickfont: { family: 'Inter', size: 10, color: c.muted }
    },
    yaxis: {
      gridcolor: c.rule, zerolinecolor: c.rule,
      showgrid: true, tickfont: { family: 'Inter', size: 10, color: c.muted }
    },
    hoverlabel: {
      bgcolor: c.white, bordercolor: c.ink,
      font: { size: 11, family: 'JetBrains Mono, monospace' }
    }
  }, extra || {});
}

const plotlyConfig = { displaylogo: false, displayModeBar: false };
```

- [ ] **Step 2 : Mettre à jour les appels Plotly.newPlot pour utiliser buildPlotlyLayout()**

Remplacer (autour des lignes 380–393) :

```javascript
Plotly.newPlot('chart-latency', [{
  y: durations, mode: 'lines', fill: 'tozeroy',
  line: { color: '#1a1a1a', width: 1.5, shape: 'spline' },
  fillcolor: 'rgba(26,26,26,0.08)',
  hovertemplate: '<b>%{y:.0f} ms</b><extra></extra>'
}], { ...plotlyLayout, height: 200, showlegend: false }, plotlyConfig);

Plotly.newPlot('chart-tokens', [{
  y: tokens, type: 'bar',
  marker: { color: '#991b1b', line: { width: 0 } },
  opacity: 0.85,
  hovertemplate: '<b>%{y:,} tokens</b><extra></extra>'
}], { ...plotlyLayout, height: 160, showlegend: false }, plotlyConfig);
```

par :

```javascript
var c = getPlotlyColors();

Plotly.newPlot('chart-latency', [{
  y: durations, mode: 'lines', fill: 'tozeroy',
  line: { color: c.ink, width: 1.5, shape: 'spline' },
  fillcolor: c.ink.startsWith('#') ? c.ink + '14' : 'rgba(26,26,26,0.08)',
  hovertemplate: '<b>%{y:.0f} ms</b><extra></extra>'
}], Object.assign(buildPlotlyLayout(), { height: 200, showlegend: false }), plotlyConfig);

Plotly.newPlot('chart-tokens', [{
  y: tokens, type: 'bar',
  marker: { color: c.accent, line: { width: 0 } },
  opacity: 0.85,
  hovertemplate: '<b>%{y:,} tokens</b><extra></extra>'
}], Object.assign(buildPlotlyLayout(), { height: 160, showlegend: false }), plotlyConfig);
```

- [ ] **Step 3 : Ajouter un MutationObserver pour re-render les charts au changement de thème**

Ajouter ce bloc à la fin du script inline, juste avant la fermeture `})();` :

```javascript
// ── Re-render Plotly au changement de thème ────────────────
new MutationObserver(function (mutations) {
  mutations.forEach(function (m) {
    if (m.attributeName === 'data-theme') {
      var latencyEl = document.getElementById('chart-latency');
      var tokensEl  = document.getElementById('chart-tokens');
      if (latencyEl && latencyEl.children.length > 0) {
        loadDashboard();
      }
    }
  });
}).observe(document.documentElement, { attributes: true });
```

- [ ] **Step 4 : Lancer les tests Plotly**

```bash
python -m pytest tests/test_ux_critiques.py -v -k "plotly or hardcoded"
```

Attendu :
```
test_dashboard_plotly_reads_css_vars PASSED
test_dashboard_no_hardcoded_plotly_paper_color PASSED
```

- [ ] **Step 5 : Lancer tous les tests du fichier**

```bash
python -m pytest tests/test_ux_critiques.py -v
```

Attendu : tous les tests `PASSED`.

- [ ] **Step 6 : Commit**

```bash
git add templates/dashboard.html
git commit -m "fix(ux): Plotly dark mode — couleurs dynamiques depuis CSS custom properties"
```

---

## Vérification finale

- [ ] **Lancer la suite complète pour s'assurer que rien n'est cassé**

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py -x 2>&1 | tail -30
```

Attendu : tous les tests passent (les tests d'intégration sont exclus car ils consomment des tokens LLM).

- [ ] **Commit de fermeture si besoin**

```bash
git add -A
git commit -m "fix(a11y): corrections critiques audit UX 6 — 7 issues résolus"
```

---

## Récapitulatif des commits attendus

| Commit | Message | Fichiers |
|--------|---------|----------|
| 1 | `test(a11y): ajout tests critiques audit UX 6 — tous en échec initial` | `tests/test_ux_critiques.py` |
| 2 | `fix(css): correction syntaxe invalide dark mode dragover overlay` | `static/luciole.css` |
| 3 | `fix(a11y): sidebar delete accessible au clavier — button + focus-visible` | `static/luciole.css`, `static/luciole-chat.js` |
| 4 | `fix(a11y): auth tabs — ARIA tablist/tab/aria-selected + role=alert sur erreurs` | `templates/login.html` |
| 5 | `fix(a11y): hiérarchie heading h1/h2/h3 sur dashboard et digest` | `templates/dashboard.html`, `templates/digest.html` |
| 6 | `fix(ux): remplacement prompt() par champ API key inline sur /digest-page` | `templates/digest.html` |
| 7 | `fix(ux): Plotly dark mode — couleurs dynamiques depuis CSS custom properties` | `templates/dashboard.html` |
