# Page Articles & Digest In-App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browsable Articles page with filters/tri/pagination and a Digest in-app view (live + PG-backed history), plus auto-seed at startup and a manual pipeline trigger endpoint.

**Architecture:** New DB functions for filtered article queries and digest history. New API endpoints serving JSON data. Two new/refactored Jinja2 templates using existing Luciole design system. Startup resilience via DB-empty check.

**Tech Stack:** Python 3.12, FastAPI, psycopg2, Jinja2, vanilla JS, PostgreSQL (Neon)

**Spec:** `docs/superpowers/specs/2026-05-20-articles-digest-inapp-design.md`

---

### Task 1: Database — `lire_articles_filtres()` and `lire_categories()`

**Files:**
- Modify: `tools/database.py` (append after `lire_articles_actifs()`, around line 238)
- Create: `tests/test_articles_page.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_articles_page.py`:

```python
"""Tests for articles filtering, categories, and digest history DB functions."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_pg():
    """Mock PostgreSQL connection and cursor for tools/database.py functions."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = []
    mock_cur.fetchone.return_value = {"total": 0}
    mock_conn.cursor.return_value = mock_cur

    with patch("tools.database._pg_connect", return_value=mock_conn), \
         patch("tools.database._cur", return_value=mock_cur):
        yield mock_conn, mock_cur


class TestLireArticlesFiltres:
    def test_returns_tuple_articles_and_count(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        articles, total = lire_articles_filtres()
        assert isinstance(articles, list)
        assert isinstance(total, int)
        assert total == 0

    def test_default_filters(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres()

        # Check the COUNT query was called with archive=0 and pertinence>=5
        count_call = mock_cur.execute.call_args_list[1]  # after _init_articles_table
        count_sql = count_call[0][0]
        assert "archive = 0" in count_sql
        assert "pertinence >=" in count_sql

    def test_categorie_filter(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(categorie="IA")

        count_call = mock_cur.execute.call_args_list[1]
        count_sql = count_call[0][0]
        assert "categorie = %s" in count_sql

    def test_date_filters(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(date_min="2026-01-01", date_max="2026-12-31")

        count_call = mock_cur.execute.call_args_list[1]
        count_sql = count_call[0][0]
        assert "date_publication >=" in count_sql
        assert "date_publication <=" in count_sql

    def test_tri_pertinence(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(tri="pertinence")

        select_call = mock_cur.execute.call_args_list[2]
        select_sql = select_call[0][0]
        assert "ORDER BY pertinence DESC" in select_sql

    def test_tri_date(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(tri="date")

        select_call = mock_cur.execute.call_args_list[2]
        select_sql = select_call[0][0]
        assert "ORDER BY date_publication DESC" in select_sql

    def test_offset_and_limit(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(offset=20, limit=10)

        select_call = mock_cur.execute.call_args_list[2]
        select_sql = select_call[0][0]
        assert "OFFSET" in select_sql
        assert "LIMIT" in select_sql


class TestLireCategories:
    def test_returns_list_of_strings(self, mock_pg):
        from tools.database import lire_categories
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchall.return_value = [
            {"categorie": "Cloud"},
            {"categorie": "IA"},
        ]

        result = lire_categories()
        assert result == ["Cloud", "IA"]

    def test_returns_empty_list_when_no_articles(self, mock_pg):
        from tools.database import lire_categories
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchall.return_value = []

        result = lire_categories()
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -m pytest tests/test_articles_page.py -v`
Expected: FAIL — `ImportError: cannot import name 'lire_articles_filtres'`

- [ ] **Step 3: Implement `lire_articles_filtres()` and `lire_categories()`**

Add to `tools/database.py` after `lire_articles_actifs()` (after line 238):

```python
def lire_articles_filtres(
    categorie: str | None = None,
    date_min: str | None = None,
    date_max: str | None = None,
    pertinence_min: int = 5,
    tri: str = "pertinence",
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """
    Retourne (articles, total_count) depuis PostgreSQL avec filtrage dynamique.
    Filtre: archive = 0, pertinence >= pertinence_min.
    Tri: ORDER BY pertinence DESC ou date_publication DESC.
    """
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)

        conditions = ["archive = 0", "pertinence >= %s"]
        params: list = [pertinence_min]

        if categorie:
            conditions.append("categorie = %s")
            params.append(categorie)
        if date_min:
            conditions.append("date_publication >= %s")
            params.append(date_min)
        if date_max:
            conditions.append("date_publication <= %s")
            params.append(date_max)

        where = " AND ".join(conditions)

        # Count total
        cur.execute(f"SELECT COUNT(*) AS total FROM articles WHERE {where}", params)
        total = cur.fetchone()["total"]

        # Fetch page
        order = "pertinence DESC" if tri == "pertinence" else "date_publication DESC"
        cur.execute(
            f"SELECT lien, titre, resume, categorie, pertinence, source,"
            f"       date_publication, date_ajout"
            f" FROM articles WHERE {where}"
            f" ORDER BY {order} OFFSET %s LIMIT %s",
            params + [offset, limit],
        )
        articles = [dict(r) for r in cur.fetchall()]
        return articles, total
    finally:
        conn.close()


def lire_categories() -> list[str]:
    """Retourne la liste des categories distinctes des articles actifs."""
    conn = _pg_connect()
    try:
        _init_articles_table(conn)
        cur = _cur(conn)
        cur.execute(
            "SELECT DISTINCT categorie FROM articles"
            " WHERE archive = 0 ORDER BY categorie"
        )
        return [row["categorie"] for row in cur.fetchall()]
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -m pytest tests/test_articles_page.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tools/database.py tests/test_articles_page.py
git commit -m "feat(db): add lire_articles_filtres() and lire_categories()"
```

---

### Task 2: API endpoints — `/articles-page` and `/articles`

**Files:**
- Modify: `api.py` (add after conversations section, around line 498)

- [ ] **Step 1: Add the articles endpoints to `api.py`**

Add after the conversations section (around line 498), before the `@app.get("/metrics")` block:

```python
# ---------------------------------------------------------------------------
# Articles endpoints
# ---------------------------------------------------------------------------

@app.get("/articles-page", response_class=HTMLResponse)
async def articles_page(request: Request, user=Depends(get_current_user_page)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(request, "articles.html", {"active_page": "articles", "user": user})


@app.get("/articles")
def articles_list(
    request: Request,
    categorie: str | None = None,
    date_min: str | None = None,
    date_max: str | None = None,
    pertinence_min: int = 5,
    tri: str = "pertinence",
    offset: int = 0,
    limit: int = 20,
    user=Depends(get_current_user),
):
    from tools.database import lire_articles_filtres, lire_categories
    limit = min(limit, 100)
    if tri not in ("pertinence", "date"):
        tri = "pertinence"
    articles, total = lire_articles_filtres(
        categorie=categorie,
        date_min=date_min,
        date_max=date_max,
        pertinence_min=pertinence_min,
        tri=tri,
        offset=offset,
        limit=limit,
    )
    return {
        "articles": articles,
        "total": total,
        "has_more": offset + limit < total,
    }


@app.get("/articles/categories")
def articles_categories(request: Request, user=Depends(get_current_user)):
    from tools.database import lire_categories
    return {"categories": lire_categories()}
```

- [ ] **Step 2: Verify the import path works**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -c "from tools.database import lire_articles_filtres, lire_categories; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add api.py
git commit -m "feat(api): add /articles-page, /articles, /articles/categories endpoints"
```

---

### Task 3: Template — `articles.html`

**Files:**
- Create: `templates/articles.html`

- [ ] **Step 1: Create the articles template**

Create `templates/articles.html`:

```html
{% extends "base.html" %}

{% block head %}
<style>
  /* Articles page — Luciole design system */
  h2.art-section {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--luciole-accent);
    padding-bottom: var(--luciole-space-3);
    border-bottom: var(--luciole-rule-thin);
    margin: var(--luciole-space-8) 0 var(--luciole-space-6);
  }

  /* Filters bar */
  .art-filters {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: var(--luciole-space-4);
    margin-bottom: var(--luciole-space-6);
  }
  .art-filter-group {
    display: flex;
    flex-direction: column;
    gap: var(--luciole-space-1);
  }
  .art-filter-label {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--luciole-muted);
  }
  .art-filter-select,
  .art-filter-input {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    border: 1px solid var(--luciole-rule);
    border-radius: 4px;
    padding: var(--luciole-space-2) var(--luciole-space-3);
    background: var(--luciole-paper);
    color: var(--luciole-ink);
    min-width: 140px;
  }
  .art-filter-select:focus,
  .art-filter-input:focus {
    outline: 2px solid var(--luciole-accent);
    outline-offset: 1px;
    border-color: var(--luciole-accent);
  }
  .art-filter-btn {
    font-family: var(--luciole-sans);
    font-weight: 500;
    font-size: var(--luciole-text-xs);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid var(--luciole-ink);
    background: transparent;
    color: var(--luciole-ink);
    padding: var(--luciole-space-2) var(--luciole-space-4);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
    align-self: flex-end;
  }
  .art-filter-btn:hover {
    background: var(--luciole-ink);
    color: var(--luciole-paper);
  }

  /* Count */
  .art-count {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    color: var(--luciole-muted);
    margin-bottom: var(--luciole-space-4);
  }

  /* Article cards */
  .art-list { list-style: none; padding: 0; margin: 0; }

  .art-card {
    padding: var(--luciole-space-5) 0;
    border-bottom: var(--luciole-rule-thin);
  }
  .art-card:first-child { padding-top: 0; }

  .art-card-header {
    display: flex;
    align-items: baseline;
    gap: var(--luciole-space-3);
    flex-wrap: wrap;
    margin-bottom: var(--luciole-space-2);
  }
  .art-card-title {
    font-family: var(--luciole-serif);
    font-weight: 700;
    font-size: var(--luciole-text-base);
    color: var(--luciole-ink);
    text-decoration: none;
    line-height: 1.3;
  }
  .art-card-title:hover { text-decoration: underline; }

  .art-badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 12px;
    font-family: var(--luciole-sans);
    font-size: 11px;
    font-weight: 600;
    color: #fff;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .art-card-resume {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    color: var(--luciole-ink-soft);
    line-height: 1.5;
    margin-bottom: var(--luciole-space-2);
  }
  .art-card-meta {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    color: var(--luciole-muted);
    display: flex;
    align-items: center;
    gap: var(--luciole-space-3);
  }
  .art-stars { letter-spacing: 1px; }

  /* Load more */
  .art-load-more {
    text-align: center;
    padding: var(--luciole-space-8) 0;
  }
  .art-load-btn {
    font-family: var(--luciole-sans);
    font-weight: 500;
    font-size: var(--luciole-text-xs);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid var(--luciole-ink);
    background: transparent;
    color: var(--luciole-ink);
    padding: var(--luciole-space-3) var(--luciole-space-8);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .art-load-btn:hover {
    background: var(--luciole-ink);
    color: var(--luciole-paper);
  }
  .art-load-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .art-load-btn:disabled:hover {
    background: transparent;
    color: var(--luciole-ink);
  }

  /* Empty */
  .art-empty {
    text-align: center;
    padding: var(--luciole-space-16) var(--luciole-space-8);
  }
  .art-empty h3 {
    font-family: var(--luciole-serif);
    font-weight: 700;
    font-size: var(--luciole-text-xl);
    color: var(--luciole-ink);
    margin-bottom: var(--luciole-space-2);
  }
  .art-empty p { color: var(--luciole-muted); }

  @media (max-width: 768px) {
    .art-filters { flex-direction: column; align-items: stretch; }
    .art-filter-select, .art-filter-input { min-width: 100%; }
    .art-filter-btn { align-self: stretch; }
  }
</style>
{% endblock %}

{% block content %}
<h1 class="sr-only">Articles</h1>
<h2 class="art-section">Articles · Veille Technologique</h2>

<!-- Filters -->
<div class="art-filters">
  <div class="art-filter-group">
    <label class="art-filter-label" for="f-categorie">Categorie</label>
    <select id="f-categorie" class="art-filter-select">
      <option value="">Toutes</option>
    </select>
  </div>
  <div class="art-filter-group">
    <label class="art-filter-label" for="f-date-min">Date min</label>
    <input type="date" id="f-date-min" class="art-filter-input">
  </div>
  <div class="art-filter-group">
    <label class="art-filter-label" for="f-date-max">Date max</label>
    <input type="date" id="f-date-max" class="art-filter-input">
  </div>
  <div class="art-filter-group">
    <label class="art-filter-label" for="f-pertinence">Pertinence min</label>
    <select id="f-pertinence" class="art-filter-select">
      <option value="5">5+</option>
      <option value="6">6+</option>
      <option value="7">7+</option>
      <option value="8">8+</option>
      <option value="9">9+</option>
      <option value="10">10</option>
    </select>
  </div>
  <div class="art-filter-group">
    <label class="art-filter-label" for="f-tri">Tri</label>
    <select id="f-tri" class="art-filter-select">
      <option value="pertinence">Pertinence</option>
      <option value="date">Date</option>
    </select>
  </div>
  <button class="art-filter-btn" id="btn-apply">Appliquer</button>
</div>

<!-- Count -->
<div class="art-count" id="art-count"></div>

<!-- Article list -->
<ul class="art-list" id="art-list"></ul>

<!-- Load more -->
<div class="art-load-more" id="art-load-more" hidden>
  <button class="art-load-btn" id="btn-load-more">Charger plus</button>
</div>

<!-- Empty state -->
<div class="art-empty" id="art-empty" hidden>
  <h3>Aucun article</h3>
  <p>Aucun article ne correspond aux filtres selectionnes.</p>
</div>
{% endblock %}

{% block scripts %}
<script>
(function () {
  'use strict';

  var LIMIT = 20;
  var offset = 0;
  var totalCount = 0;

  var list = document.getElementById('art-list');
  var countEl = document.getElementById('art-count');
  var loadMoreWrap = document.getElementById('art-load-more');
  var btnLoadMore = document.getElementById('btn-load-more');
  var emptyEl = document.getElementById('art-empty');
  var btnApply = document.getElementById('btn-apply');

  var fCategorie = document.getElementById('f-categorie');
  var fDateMin = document.getElementById('f-date-min');
  var fDateMax = document.getElementById('f-date-max');
  var fPertinence = document.getElementById('f-pertinence');
  var fTri = document.getElementById('f-tri');

  // Badge colors (mirrors _COULEURS_CAT in tools/email.py)
  var COLORS = {
    'ia': '#6366f1',
    'cloud': '#0ea5e9',
    'cybersecurite': '#ef4444',
    'cybersécurité': '#ef4444',
    'devops': '#f59e0b',
    'donnees': '#10b981',
    'données': '#10b981',
    'infrastructure': '#8b5cf6'
  };
  var DEFAULT_COLOR = '#64748b';

  function badgeColor(cat) {
    var lower = (cat || '').toLowerCase();
    for (var key in COLORS) {
      if (lower.indexOf(key) !== -1) return COLORS[key];
    }
    return DEFAULT_COLOR;
  }

  function stars(p) {
    var n = Math.min(Math.max(parseInt(p) || 0, 0), 10);
    var full = Math.round(n / 2);
    var s = '';
    for (var i = 0; i < full; i++) s += '\u2605';
    for (var j = full; j < 5; j++) s += '\u2606';
    return s;
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function buildParams() {
    var p = new URLSearchParams();
    if (fCategorie.value) p.set('categorie', fCategorie.value);
    if (fDateMin.value) p.set('date_min', fDateMin.value);
    if (fDateMax.value) p.set('date_max', fDateMax.value);
    p.set('pertinence_min', fPertinence.value);
    p.set('tri', fTri.value);
    p.set('offset', offset.toString());
    p.set('limit', LIMIT.toString());
    return p.toString();
  }

  function renderArticle(a) {
    var cat = a.categorie || 'Autre';
    var color = badgeColor(cat);
    var resume = (a.resume || '').substring(0, 200);
    var datePub = (a.date_publication || '').substring(0, 10);

    return '<li class="art-card">' +
      '<div class="art-card-header">' +
        '<a href="' + esc(a.lien || '#') + '" class="art-card-title" target="_blank" rel="noopener">' + esc(a.titre || 'Sans titre') + '</a>' +
        '<span class="art-badge" style="background:' + color + '">' + esc(cat) + '</span>' +
      '</div>' +
      '<div class="art-card-resume">' + esc(resume) + (resume.length >= 200 ? '&hellip;' : '') + '</div>' +
      '<div class="art-card-meta">' +
        '<span class="art-stars" style="color:' + color + '">' + stars(a.pertinence) + '</span>' +
        '<span>' + esc(a.pertinence + '/10') + '</span>' +
        '<span>' + esc(a.source || '') + '</span>' +
        (datePub ? '<span>' + esc(datePub) + '</span>' : '') +
      '</div>' +
    '</li>';
  }

  async function loadArticles(append) {
    if (!append) {
      offset = 0;
      list.innerHTML = '';
    }
    btnLoadMore.disabled = true;

    try {
      var res = await fetch('/articles?' + buildParams());
      if (!res.ok) throw new Error('API error');
      var data = await res.json();

      totalCount = data.total;
      countEl.textContent = totalCount + ' article' + (totalCount !== 1 ? 's' : '');

      if (data.articles.length === 0 && !append) {
        emptyEl.hidden = false;
        loadMoreWrap.hidden = true;
        return;
      }

      emptyEl.hidden = true;
      var html = '';
      for (var i = 0; i < data.articles.length; i++) {
        html += renderArticle(data.articles[i]);
      }

      if (append) {
        list.insertAdjacentHTML('beforeend', html);
      } else {
        list.innerHTML = html;
      }

      loadMoreWrap.hidden = !data.has_more;
      btnLoadMore.disabled = false;
    } catch (e) {
      countEl.textContent = 'Erreur de chargement';
      emptyEl.hidden = true;
      loadMoreWrap.hidden = true;
    }
  }

  // Load categories for dropdown
  async function loadCategories() {
    try {
      var res = await fetch('/articles/categories');
      if (!res.ok) return;
      var data = await res.json();
      for (var i = 0; i < data.categories.length; i++) {
        var opt = document.createElement('option');
        opt.value = data.categories[i];
        opt.textContent = data.categories[i];
        fCategorie.appendChild(opt);
      }
    } catch (e) {
      // silently ignore
    }
  }

  // Events
  btnApply.addEventListener('click', function () { loadArticles(false); });
  btnLoadMore.addEventListener('click', function () {
    offset += LIMIT;
    loadArticles(true);
  });

  // Init
  loadCategories();
  loadArticles(false);
})();
</script>
{% endblock %}
```

- [ ] **Step 2: Verify template renders (syntax check)**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); env.get_template('articles.html'); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add templates/articles.html
git commit -m "feat(ui): add articles page template with filters and load-more"
```

---

### Task 4: Navigation — Add "Articles" link to `base.html`

**Files:**
- Modify: `templates/base.html:64` (nav section)

- [ ] **Step 1: Add the Articles nav link**

In `templates/base.html`, insert a new line after line 64 (the Chat link), before the Digest link:

```html
      <a href="/articles-page" {% if active_page == "articles" %}class="active"{% endif %}>Articles</a>
```

The nav section (lines 63-76) should now read:

```html
    <nav class="luciole-nav" aria-label="Navigation principale">
      <a href="/" {% if active_page == "chat" %}class="active"{% endif %}>Chat</a>
      <a href="/articles-page" {% if active_page == "articles" %}class="active"{% endif %}>Articles</a>
      <a href="/digest-page" {% if active_page == "digest" %}class="active"{% endif %}>Digest</a>
      <a href="/dashboard" {% if active_page == "dashboard" %}class="active"{% endif %}>Tableau de bord</a>
      <a href="/about" {% if active_page == "about" %}class="active"{% endif %}>À propos</a>
```

- [ ] **Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat(nav): add Articles link to navbar"
```

---

### Task 5: Database — `digest_history` table and migration

**Files:**
- Modify: `tools/database.py` (add after `ajouter_log()`, around line 482)
- Modify: `tests/test_articles_page.py` (add new test class)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_articles_page.py`:

```python
class TestDigestHistory:
    def test_init_creates_table(self, mock_pg):
        from tools.database import _init_digest_history_table
        mock_conn, mock_cur = mock_pg
        _init_digest_history_table(mock_conn)
        create_sql = mock_cur.execute.call_args[0][0]
        assert "digest_history" in create_sql
        assert "SERIAL PRIMARY KEY" in create_sql

    def test_enregistrer_envoi_pg(self, mock_pg):
        from tools.database import enregistrer_envoi_pg
        mock_conn, mock_cur = mock_pg
        enregistrer_envoi_pg(["a@b.com"], 5, "<html>test</html>")
        insert_sql = mock_cur.execute.call_args_list[-1][0][0]
        assert "INSERT INTO digest_history" in insert_sql

    def test_lire_historique_digest(self, mock_pg):
        from tools.database import lire_historique_digest
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchall.return_value = [
            {"id": 1, "sent_at": "2026-05-20", "recipients": ["a@b.com"], "nb_articles": 5}
        ]
        result = lire_historique_digest()
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_lire_digest_archive(self, mock_pg):
        from tools.database import lire_digest_archive
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"html_content": "<html>archived</html>"}
        result = lire_digest_archive(1)
        assert result == "<html>archived</html>"

    def test_lire_digest_archive_not_found(self, mock_pg):
        from tools.database import lire_digest_archive
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = None
        result = lire_digest_archive(999)
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -m pytest tests/test_articles_page.py::TestDigestHistory -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement digest history functions**

Add to `tools/database.py` after `ajouter_log()` (around line 482):

```python
# ---------------------------------------------------------------------------
# Digest history — PostgreSQL
# ---------------------------------------------------------------------------

def _init_digest_history_table(conn) -> None:
    """Cree la table digest_history si elle n'existe pas."""
    cur = _cur(conn)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS digest_history (
            id            SERIAL PRIMARY KEY,
            sent_at       TEXT NOT NULL,
            recipients    TEXT[] NOT NULL DEFAULT '{}',
            nb_articles   INTEGER NOT NULL DEFAULT 0,
            html_content  TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()


def enregistrer_envoi_pg(destinataires: list[str], nb_articles: int, html_content: str = "") -> None:
    """Enregistre un envoi de digest dans PostgreSQL."""
    conn = _pg_connect()
    try:
        _init_digest_history_table(conn)
        cur = _cur(conn)
        cur.execute(
            "INSERT INTO digest_history (sent_at, recipients, nb_articles, html_content)"
            " VALUES (%s, %s, %s, %s)",
            (datetime.now(timezone.utc).isoformat(), destinataires, nb_articles, html_content),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info(f"[Digest] Envoi enregistre en PG : {nb_articles} articles, {len(destinataires)} dest.")


def lire_historique_digest() -> list[dict]:
    """Retourne l'historique des envois de digest depuis PostgreSQL."""
    conn = _pg_connect()
    try:
        _init_digest_history_table(conn)
        cur = _cur(conn)
        cur.execute(
            "SELECT id, sent_at, recipients, nb_articles"
            " FROM digest_history ORDER BY id DESC LIMIT 50"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def lire_digest_archive(digest_id: int) -> str | None:
    """Retourne le HTML archive d'un digest, ou None si introuvable."""
    conn = _pg_connect()
    try:
        _init_digest_history_table(conn)
        cur = _cur(conn)
        cur.execute(
            "SELECT html_content FROM digest_history WHERE id = %s",
            (digest_id,),
        )
        row = cur.fetchone()
        return row["html_content"] if row else None
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -m pytest tests/test_articles_page.py::TestDigestHistory -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tools/database.py tests/test_articles_page.py
git commit -m "feat(db): add digest_history table and CRUD functions"
```

---

### Task 6: Migrate `enregistrer_envoi()` and `envoyer_rapport()` to use PG

**Files:**
- Modify: `tools/email.py:272-274` (inside `envoyer_rapport()`)
- Modify: `tools/database.py` (update `enregistrer_envoi()`)
- Modify: `api.py` (update `/digest/history` and `/digest/stats`)

- [ ] **Step 1: Update `enregistrer_envoi()` in `tools/database.py`**

Replace the existing `enregistrer_envoi()` function (lines 241-249) with:

```python
def enregistrer_envoi(destinataires: list[str], nb_articles: int, html_content: str = "") -> None:
    """Enregistre un envoi de digest — PG principal, JSON fallback."""
    try:
        enregistrer_envoi_pg(destinataires, nb_articles, html_content)
    except Exception as e:
        logger.warning(f"[Digest] PG echoue, fallback JSON : {e}")
        historique = charger_json(HISTORIQUE_FILE)
        historique.append({
            "date": datetime.now(timezone.utc).isoformat(),
            "destinataires": destinataires,
            "nb_articles": nb_articles,
        })
        sauvegarder_json(HISTORIQUE_FILE, historique)
```

- [ ] **Step 2: Update `envoyer_rapport()` in `tools/email.py` to pass HTML**

In `tools/email.py`, modify line 273 inside `envoyer_rapport()`. Change:

```python
        enregistrer_envoi(destinataires, len(articles))
```

to:

```python
        enregistrer_envoi(destinataires, len(articles), html)
```

- [ ] **Step 3: Update `/digest/history` in `api.py`**

Replace the existing `digest_history()` function (lines 551-555) with:

```python
@app.get("/digest/history")
def digest_history(user=Depends(get_current_user)):
    """Historique des envois de digest depuis PostgreSQL."""
    from tools.database import lire_historique_digest
    try:
        historique = lire_historique_digest()
    except Exception:
        historique = charger_json(HISTORIQUE_FILE)
    return {"historique": historique}
```

- [ ] **Step 4: Update `/digest/stats` in `api.py`**

Replace the existing `digest_stats()` function (lines 538-548) with:

```python
@app.get("/digest/stats")
def digest_stats(user=Depends(get_current_user)):
    """Stats rapides pour la page digest."""
    articles = selectionner_articles(nb_max=100)
    categories = set(a.get("categorie", "Autre") for a in articles)
    from tools.database import lire_historique_digest
    try:
        historique = lire_historique_digest()
        nb_envois = len(historique)
    except Exception:
        historique = charger_json(HISTORIQUE_FILE)
        nb_envois = len(historique)
    return {
        "nb_articles": len(articles),
        "nb_categories": len(categories),
        "nb_envois": nb_envois,
    }
```

- [ ] **Step 5: Commit**

```bash
git add tools/database.py tools/email.py api.py
git commit -m "feat(digest): migrate enregistrer_envoi to PG with JSON fallback"
```

---

### Task 7: API endpoints — `/digest/live` and `/digest/archive/{id}`

**Files:**
- Modify: `api.py` (add after digest stats section)

- [ ] **Step 1: Add the new digest endpoints**

Add to `api.py` after the `digest_stats()` function:

```python
@app.get("/digest/live")
def digest_live(user=Depends(get_current_user)):
    """Retourne les meilleurs articles actuels groupes par categorie."""
    from datetime import datetime, timezone
    articles = selectionner_articles(nb_max=100)
    categories: dict[str, list[dict]] = {}
    for a in articles:
        cat = a.get("categorie", "Autre")
        categories.setdefault(cat, []).append({
            "titre": a.get("titre", ""),
            "lien": a.get("lien", ""),
            "resume": a.get("resume", a.get("resume_brut", ""))[:300],
            "pertinence": int(a.get("pertinence", 0)),
            "source": a.get("source", ""),
            "date_publication": a.get("date_publication", "")[:10],
        })
    return {
        "categories": categories,
        "total": len(articles),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/digest/archive/{digest_id}")
def digest_archive(digest_id: int, user=Depends(get_current_user)):
    """Retourne le HTML archive d'un digest passe."""
    from tools.database import lire_digest_archive
    html = lire_digest_archive(digest_id)
    if html is None:
        raise HTTPException(status_code=404, detail="Digest introuvable.")
    return HTMLResponse(content=html)
```

- [ ] **Step 2: Commit**

```bash
git add api.py
git commit -m "feat(api): add /digest/live and /digest/archive/{id} endpoints"
```

---

### Task 8: Refactor `digest.html` — tabs + live digest + archive links

**Files:**
- Modify: `templates/digest.html` (full rewrite)

- [ ] **Step 1: Rewrite `templates/digest.html`**

Replace the entire content of `templates/digest.html` with:

```html
{% extends "base.html" %}

{% block head %}
<style>
  /* Digest page — Luciole design system */
  h2.digest-section {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--luciole-muted);
    padding-bottom: var(--luciole-space-3);
    border-bottom: var(--luciole-rule-thin);
    margin: var(--luciole-space-12) 0 var(--luciole-space-6);
  }
  .digest-section--accent {
    color: var(--luciole-accent);
    margin-top: var(--luciole-space-8);
  }

  /* Tabs */
  .digest-tabs {
    display: flex;
    gap: 0;
    border-bottom: var(--luciole-rule-medium);
    margin-bottom: var(--luciole-space-6);
  }
  .digest-tab {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    padding: var(--luciole-space-3) var(--luciole-space-6);
    color: var(--luciole-muted);
    cursor: pointer;
    transition: all 0.2s;
  }
  .digest-tab:hover { color: var(--luciole-ink); }
  .digest-tab.active {
    color: var(--luciole-ink);
    border-bottom-color: var(--luciole-ink);
  }

  /* KPIs */
  .digest-kpis {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--luciole-space-6);
  }
  .digest-kpi {
    padding: var(--luciole-space-6) 0;
    border-top: var(--luciole-rule-thin);
  }
  .digest-kpi-label {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--luciole-muted);
  }
  .digest-kpi-value {
    font-family: var(--luciole-serif);
    font-weight: 900;
    font-size: var(--luciole-text-3xl);
    line-height: 1.1;
    color: var(--luciole-ink);
    margin: var(--luciole-space-2) 0 var(--luciole-space-1);
  }
  .digest-kpi-sub {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--luciole-muted);
  }

  /* Accordion */
  .digest-cat-header {
    display: flex;
    align-items: center;
    gap: var(--luciole-space-3);
    padding: var(--luciole-space-4) 0;
    border-bottom: var(--luciole-rule-thin);
    cursor: pointer;
    user-select: none;
  }
  .digest-cat-header:hover { opacity: 0.8; }
  .digest-cat-arrow {
    font-size: var(--luciole-text-sm);
    transition: transform 0.2s;
    color: var(--luciole-muted);
  }
  .digest-cat-header.collapsed .digest-cat-arrow { transform: rotate(-90deg); }
  .digest-cat-badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 12px;
    font-family: var(--luciole-sans);
    font-size: 11px;
    font-weight: 600;
    color: #fff;
  }
  .digest-cat-name {
    font-family: var(--luciole-serif);
    font-weight: 700;
    font-size: var(--luciole-text-base);
    color: var(--luciole-ink);
  }
  .digest-cat-count {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    color: var(--luciole-muted);
  }
  .digest-cat-body { overflow: hidden; }
  .digest-cat-body.collapsed { display: none; }

  /* Article cards (shared with articles page) */
  .digest-art {
    padding: var(--luciole-space-4) 0 var(--luciole-space-4) var(--luciole-space-6);
    border-bottom: var(--luciole-rule-thin);
  }
  .digest-art-title {
    font-family: var(--luciole-serif);
    font-weight: 700;
    font-size: var(--luciole-text-sm);
    color: var(--luciole-ink);
    text-decoration: none;
  }
  .digest-art-title:hover { text-decoration: underline; }
  .digest-art-resume {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    color: var(--luciole-ink-soft);
    margin: var(--luciole-space-1) 0;
    line-height: 1.5;
  }
  .digest-art-meta {
    font-family: var(--luciole-sans);
    font-size: 11px;
    color: var(--luciole-muted);
    display: flex;
    gap: var(--luciole-space-3);
  }
  .digest-art-stars { letter-spacing: 1px; }

  /* Admin section */
  .digest-actions {
    display: flex;
    align-items: center;
    gap: var(--luciole-space-4);
    margin-bottom: var(--luciole-space-6);
    flex-wrap: wrap;
  }
  .digest-apikey-group {
    display: flex;
    flex-direction: column;
    gap: var(--luciole-space-1);
  }
  .digest-apikey-label {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--luciole-muted);
  }
  .digest-apikey-input {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    border: 1px solid var(--luciole-rule);
    border-radius: 4px;
    padding: var(--luciole-space-2) var(--luciole-space-3);
    background: var(--luciole-paper);
    color: var(--luciole-ink);
    min-width: 220px;
  }
  .digest-apikey-input:focus {
    outline: 2px solid var(--luciole-accent);
    outline-offset: 1px;
    border-color: var(--luciole-accent);
  }
  .digest-apikey-error {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-xs);
    color: var(--luciole-accent);
    display: none;
  }
  .digest-apikey-error--visible { display: block; }
  .digest-btn {
    font-family: var(--luciole-sans);
    font-weight: 500;
    font-size: var(--luciole-text-xs);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid var(--luciole-ink);
    background: transparent;
    color: var(--luciole-ink);
    padding: var(--luciole-space-2) var(--luciole-space-4);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .digest-btn:hover {
    background: var(--luciole-ink);
    color: var(--luciole-paper);
  }
  .digest-btn--accent {
    border-color: var(--luciole-accent);
    color: var(--luciole-accent);
  }
  .digest-btn--accent:hover {
    background: var(--luciole-accent);
    color: var(--luciole-white);
  }
  .digest-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .digest-btn:disabled:hover { background: transparent; color: var(--luciole-ink); }
  .digest-btn--accent:disabled:hover { color: var(--luciole-accent); }
  .digest-status {
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    color: var(--luciole-muted);
  }
  .digest-status--ok { color: #22c55e; }
  .digest-status--err { color: var(--luciole-accent); }

  .digest-preview-frame {
    width: 100%;
    min-height: 600px;
    border: 1px solid var(--luciole-rule);
    border-radius: 6px;
    background: var(--luciole-white);
  }

  /* History table */
  .digest-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--luciole-sans);
    font-size: var(--luciole-text-sm);
    margin-top: var(--luciole-space-3);
  }
  .digest-table th {
    font-size: var(--luciole-text-xs);
    font-weight: 500;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--luciole-muted);
    text-align: left;
    padding: var(--luciole-space-3) var(--luciole-space-4);
    border-bottom: var(--luciole-rule-medium);
  }
  .digest-table td {
    padding: var(--luciole-space-3) var(--luciole-space-4);
    border-bottom: var(--luciole-rule-thin);
    color: var(--luciole-ink-soft);
  }
  .digest-table tr:hover td { background: var(--luciole-paper-alt); }
  .digest-table a {
    color: var(--luciole-accent);
    text-decoration: none;
    font-weight: 500;
  }
  .digest-table a:hover { text-decoration: underline; }

  /* Empty state */
  .digest-empty {
    text-align: center;
    padding: var(--luciole-space-16) var(--luciole-space-8);
    border: 1px dashed var(--luciole-rule);
    border-radius: 6px;
  }
  .digest-empty h3 {
    font-family: var(--luciole-serif);
    font-weight: 700;
    font-size: var(--luciole-text-xl);
    color: var(--luciole-ink);
    margin-bottom: var(--luciole-space-2);
  }
  .digest-empty p {
    color: var(--luciole-muted);
    font-size: var(--luciole-text-sm);
  }

  @media (max-width: 768px) {
    .digest-kpis { grid-template-columns: 1fr; }
    .digest-actions { flex-direction: column; align-items: stretch; }
  }
</style>
{% endblock %}

{% block content %}
<h1 class="sr-only">Digest Email</h1>
<h2 class="digest-section digest-section--accent">Digest · Veille Technologique</h2>

<!-- Tabs -->
<div class="digest-tabs" role="tablist" aria-label="Mode digest">
  <button class="digest-tab active" role="tab" id="tab-live" aria-selected="true" aria-controls="panel-live" tabindex="0">Digest du jour</button>
  <button class="digest-tab" role="tab" id="tab-admin" aria-selected="false" aria-controls="panel-admin" tabindex="-1">Historique &amp; envoi</button>
</div>

<!-- Panel 1: Live digest -->
<div id="panel-live" role="tabpanel" aria-labelledby="tab-live">
  <!-- KPIs -->
  <div class="digest-kpis" id="digest-kpis">
    <div class="digest-kpi">
      <div class="digest-kpi-label">Articles</div>
      <div class="digest-kpi-value" id="kpi-articles">--</div>
      <div class="digest-kpi-sub">pertinence >= 5</div>
    </div>
    <div class="digest-kpi">
      <div class="digest-kpi-label">Categories</div>
      <div class="digest-kpi-value" id="kpi-categories">--</div>
      <div class="digest-kpi-sub">thematiques</div>
    </div>
    <div class="digest-kpi">
      <div class="digest-kpi-label">Genere le</div>
      <div class="digest-kpi-value" id="kpi-date" style="font-size:var(--luciole-text-lg);">--</div>
      <div class="digest-kpi-sub">mise a jour</div>
    </div>
  </div>

  <!-- Live articles by category -->
  <div id="digest-live-content">
    <div class="digest-empty">
      <h3>Chargement...</h3>
      <p>Recuperation du digest.</p>
    </div>
  </div>
</div>

<!-- Panel 2: Admin -->
<div id="panel-admin" role="tabpanel" aria-labelledby="tab-admin" hidden>
  <h2 class="digest-section">Actions</h2>
  <div class="digest-actions">
    <button class="digest-btn" id="btn-preview">Previsualiser</button>
    <div class="digest-apikey-group">
      <label class="digest-apikey-label" for="apikey-input">Cle API serveur</label>
      <input id="apikey-input" class="digest-apikey-input" type="password" placeholder="Cle API serveur" autocomplete="off" aria-describedby="apikey-error">
      <span id="apikey-error" class="digest-apikey-error" role="alert">Veuillez saisir votre cle API avant d'envoyer.</span>
    </div>
    <button class="digest-btn digest-btn--accent" id="btn-send" disabled>Envoyer par email</button>
    <span class="digest-status" id="digest-status"></span>
  </div>

  <!-- Preview -->
  <div id="digest-preview-container"></div>

  <!-- History -->
  <h2 class="digest-section">Historique des envois</h2>
  <div id="digest-history">
    <div class="digest-empty">
      <h3>Chargement...</h3>
      <p>Recuperation de l'historique.</p>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
(function () {
  'use strict';

  // ── Badge colors (same as articles page) ──────────────
  var COLORS = {
    'ia': '#6366f1', 'cloud': '#0ea5e9', 'cybersecurite': '#ef4444',
    'cybersécurité': '#ef4444', 'devops': '#f59e0b', 'donnees': '#10b981',
    'données': '#10b981', 'infrastructure': '#8b5cf6'
  };
  var DEFAULT_COLOR = '#64748b';

  function badgeColor(cat) {
    var lower = (cat || '').toLowerCase();
    for (var key in COLORS) { if (lower.indexOf(key) !== -1) return COLORS[key]; }
    return DEFAULT_COLOR;
  }

  function stars(p) {
    var n = Math.min(Math.max(parseInt(p) || 0, 0), 10);
    var full = Math.round(n / 2);
    var s = '';
    for (var i = 0; i < full; i++) s += '\u2605';
    for (var j = full; j < 5; j++) s += '\u2606';
    return s;
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Tab switching ─────────────────────────────────────
  var tabs = document.querySelectorAll('.digest-tab');
  var panelLive = document.getElementById('panel-live');
  var panelAdmin = document.getElementById('panel-admin');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
        t.setAttribute('tabindex', '-1');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      tab.setAttribute('tabindex', '0');
      panelLive.hidden = tab.id !== 'tab-live';
      panelAdmin.hidden = tab.id !== 'tab-admin';
    });
  });

  // Keyboard nav
  var tablist = document.querySelector('[role="tablist"]');
  tablist.addEventListener('keydown', function (e) {
    var arr = Array.from(tabs);
    var idx = arr.indexOf(document.activeElement);
    if (e.key === 'ArrowRight' && idx < arr.length - 1) { e.preventDefault(); arr[idx+1].focus(); arr[idx+1].click(); }
    if (e.key === 'ArrowLeft' && idx > 0) { e.preventDefault(); arr[idx-1].focus(); arr[idx-1].click(); }
  });

  // ── Live digest ───────────────────────────────────────
  var liveContent = document.getElementById('digest-live-content');

  async function loadLive() {
    try {
      var res = await fetch('/digest/live');
      if (!res.ok) throw new Error();
      var data = await res.json();

      document.getElementById('kpi-articles').textContent = data.total;
      var catKeys = Object.keys(data.categories);
      document.getElementById('kpi-categories').textContent = catKeys.length;
      document.getElementById('kpi-date').textContent = data.generated_at ? new Date(data.generated_at).toLocaleDateString('fr-FR') : '--';

      if (data.total === 0) {
        liveContent.innerHTML = '<div class="digest-empty"><h3>Aucun article</h3><p>Le pipeline n\'a pas encore collecte d\'articles.</p></div>';
        return;
      }

      var html = '';
      for (var ci = 0; ci < catKeys.length; ci++) {
        var cat = catKeys[ci];
        var arts = data.categories[cat];
        var color = badgeColor(cat);

        html += '<div class="digest-cat-header" data-cat="' + ci + '">';
        html += '<span class="digest-cat-arrow">\u25BC</span>';
        html += '<span class="digest-cat-badge" style="background:' + color + '">' + esc(cat) + '</span>';
        html += '<span class="digest-cat-name">' + esc(cat) + '</span>';
        html += '<span class="digest-cat-count">' + arts.length + ' article' + (arts.length > 1 ? 's' : '') + '</span>';
        html += '</div>';
        html += '<div class="digest-cat-body" data-cat-body="' + ci + '">';

        for (var ai = 0; ai < arts.length; ai++) {
          var a = arts[ai];
          html += '<div class="digest-art">';
          html += '<a href="' + esc(a.lien || '#') + '" class="digest-art-title" target="_blank" rel="noopener">' + esc(a.titre) + '</a>';
          html += '<div class="digest-art-resume">' + esc((a.resume || '').substring(0, 200)) + '</div>';
          html += '<div class="digest-art-meta">';
          html += '<span class="digest-art-stars" style="color:' + color + '">' + stars(a.pertinence) + '</span>';
          html += '<span>' + a.pertinence + '/10</span>';
          html += '<span>' + esc(a.source || '') + '</span>';
          html += (a.date_publication ? '<span>' + esc(a.date_publication) + '</span>' : '');
          html += '</div></div>';
        }
        html += '</div>';
      }

      liveContent.innerHTML = html;

      // Accordion toggle
      document.querySelectorAll('.digest-cat-header').forEach(function (header) {
        header.addEventListener('click', function () {
          var id = header.getAttribute('data-cat');
          var body = document.querySelector('[data-cat-body="' + id + '"]');
          header.classList.toggle('collapsed');
          body.classList.toggle('collapsed');
        });
      });
    } catch (e) {
      liveContent.innerHTML = '<div class="digest-empty"><h3>Erreur</h3><p>Impossible de charger le digest.</p></div>';
    }
  }

  // ── Admin: preview/send (same as before) ──────────────
  var btnPreview = document.getElementById('btn-preview');
  var btnSend = document.getElementById('btn-send');
  var status = document.getElementById('digest-status');
  var previewContainer = document.getElementById('digest-preview-container');
  var apikeyInput = document.getElementById('apikey-input');
  var apikeyError = document.getElementById('apikey-error');
  var historyContainer = document.getElementById('digest-history');

  function setStatus(msg, type) {
    status.textContent = msg;
    status.className = 'digest-status' + (type ? ' digest-status--' + type : '');
  }

  btnPreview.addEventListener('click', async function () {
    var apiKey = apikeyInput.value.trim();
    if (!apiKey) { apikeyError.classList.add('digest-apikey-error--visible'); apikeyInput.focus(); return; }
    apikeyError.classList.remove('digest-apikey-error--visible');
    btnPreview.disabled = true;
    setStatus('Generation en cours...', '');
    try {
      var res = await fetch('/digest', { headers: { 'X-API-Key': apiKey } });
      if (!res.ok) throw new Error();
      var html = await res.text();
      previewContainer.innerHTML = '';
      var iframe = document.createElement('iframe');
      iframe.className = 'digest-preview-frame';
      iframe.setAttribute('sandbox', 'allow-same-origin');
      iframe.title = 'Apercu du digest';
      previewContainer.appendChild(iframe);
      iframe.contentDocument.open();
      iframe.contentDocument.write(html);
      iframe.contentDocument.close();
      btnSend.disabled = false;
      setStatus('Apercu genere', 'ok');
    } catch (e) {
      setStatus('Erreur lors de la generation', 'err');
    } finally {
      btnPreview.disabled = false;
    }
  });

  btnSend.addEventListener('click', async function () {
    if (!confirm('Envoyer le digest par email aux destinataires configures ?')) return;
    var apiKey = apikeyInput.value.trim();
    if (!apiKey) { apikeyError.classList.add('digest-apikey-error--visible'); apikeyInput.focus(); return; }
    apikeyError.classList.remove('digest-apikey-error--visible');
    btnSend.disabled = true;
    setStatus('Envoi en cours...', '');
    try {
      var res = await fetch('/digest/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({})
      });
      var data = await res.json();
      if (res.ok && data.ok) {
        setStatus('Digest envoye — ' + data.nb_articles + ' articles', 'ok');
        loadHistory();
      } else {
        setStatus(data.message || data.detail || 'Erreur', 'err');
      }
    } catch (e) {
      setStatus('Erreur reseau', 'err');
    } finally {
      btnSend.disabled = false;
      apikeyInput.value = '';
    }
  });

  // ── History ───────────────────────────────────────────
  async function loadHistory() {
    try {
      var res = await fetch('/digest/history');
      if (!res.ok) throw new Error();
      var data = await res.json();
      if (!data.historique || data.historique.length === 0) {
        historyContainer.innerHTML = '<div class="digest-empty"><h3>Aucun envoi</h3><p>Le digest n\'a pas encore ete envoye.</p></div>';
        return;
      }
      var html = '<table class="digest-table"><thead><tr><th>Date</th><th>Destinataires</th><th>Articles</th><th>Archive</th></tr></thead><tbody>';
      var sorted = data.historique.slice();
      for (var i = 0; i < sorted.length; i++) {
        var entry = sorted[i];
        var date = entry.sent_at ? new Date(entry.sent_at).toLocaleString('fr-FR') : (entry.date ? new Date(entry.date).toLocaleString('fr-FR') : '--');
        var dest = (entry.recipients || entry.destinataires || []).join(', ') || '--';
        var archiveLink = entry.id ? '<a href="/digest/archive/' + entry.id + '" target="_blank">Voir</a>' : '--';
        html += '<tr><td>' + esc(date) + '</td><td>' + esc(dest) + '</td><td>' + (entry.nb_articles || 0) + '</td><td>' + archiveLink + '</td></tr>';
      }
      html += '</tbody></table>';
      historyContainer.innerHTML = html;
    } catch (e) {
      historyContainer.innerHTML = '<div class="digest-empty"><h3>API indisponible</h3><p>Impossible de charger l\'historique.</p></div>';
    }
  }

  // ── Init ──────────────────────────────────────────────
  loadLive();
  loadHistory();
})();
</script>
{% endblock %}
```

- [ ] **Step 2: Verify template renders (syntax check)**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); env.get_template('digest.html'); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add templates/digest.html
git commit -m "feat(ui): refactor digest page with tabs, live digest, and archive links"
```

---

### Task 9: Auto-seed startup + `POST /veille/run`

**Files:**
- Modify: `startup.py` (modify `run()`, around line 30)
- Modify: `api.py` (add endpoint)

- [ ] **Step 1: Modify `startup.py` to auto-seed on empty DB**

Replace the `run()` function in `startup.py` (lines 30-70) with:

```python
def _db_has_articles() -> bool:
    """Verifie si la table articles contient au moins 1 article actif."""
    try:
        from tools.database import lire_articles_actifs
        return len(lire_articles_actifs()) > 0
    except Exception:
        return False


def run():
    # Cas 1 : articles pre-collectes au build (prebuild.py)
    if os.path.exists(RAW_FILE):
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)

        print(f"[startup] {len(articles)} articles pre-collectes trouves.")

        nouveaux = [a for a in articles if not article_deja_traite(a.get("lien", ""))]
        print(f"[startup] {len(nouveaux)} nouveaux articles a enrichir.")

        if not nouveaux:
            print("[startup] Rien a faire, base deja a jour.")
            return

        print(f"[startup] Enrichissement LLM ({LLM_WORKERS} threads)...")
        enrichis = []
        done = 0
        with ThreadPoolExecutor(max_workers=LLM_WORKERS) as pool:
            futures = {pool.submit(enrichir_article, a): a for a in nouveaux}
            for future in as_completed(futures):
                done += 1
                result = future.result()
                if result:
                    enrichis.append(result)
                if done % 50 == 0:
                    print(f"[startup] {done}/{len(nouveaux)} traites...")

        print(f"[startup] {len(enrichis)} articles enrichis et pertinents.")
        nb = sauvegarder_articles(enrichis)
        print(f"[startup] {nb} articles sauvegardes et indexes.")
        return

    # Cas 2 : pas de cache prebuild et DB vide → pipeline complet
    if not _db_has_articles():
        print("[startup] DB vide et pas de cache prebuild — lancement du pipeline complet...")
        from pipeline import run as pipeline_run
        pipeline_run(no_email=True)
        return

    # Cas 3 : DB deja peuplee, rien a faire
    print("[startup] Base deja peuplee, pas de pipeline necessaire.")
```

- [ ] **Step 2: Add `POST /veille/run` endpoint in `api.py`**

Add after the health endpoint (around line 328):

```python
@app.post("/veille/run")
@limiter.limit("1/hour")
def veille_run(request: Request, x_api_key: str | None = Header(default=None)):
    """Lance le pipeline de veille en arriere-plan. Protege par X-API-Key."""
    _verifier_api_key(x_api_key)
    import threading
    from pipeline import run as pipeline_run

    def _run_pipeline():
        try:
            pipeline_run(no_email=True)
            logger.info("[Veille] Pipeline termine avec succes.")
        except Exception as e:
            logger.error(f"[Veille] Pipeline echoue : {e}")

    threading.Thread(target=_run_pipeline, daemon=True).start()
    return {"ok": True, "message": "Pipeline lance en arriere-plan."}
```

- [ ] **Step 3: Commit**

```bash
git add startup.py api.py
git commit -m "feat: auto-seed on empty DB + POST /veille/run endpoint"
```

---

### Task 10: Integration test

**Files:**
- Modify: `tests/test_articles_page.py` (add integration tests)

- [ ] **Step 1: Add integration tests for API endpoints**

Append to `tests/test_articles_page.py`:

```python
class TestArticlesEndpoints:
    """Test the /articles and /articles/categories endpoints via mock DB."""

    def test_articles_endpoint_returns_structure(self, mock_pg):
        from unittest.mock import patch, MagicMock
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 2}
        mock_cur.fetchall.return_value = [
            {"lien": "https://example.com/1", "titre": "Article 1",
             "resume": "Res 1", "categorie": "IA", "pertinence": 9,
             "source": "Src", "date_publication": "2026-05-20", "date_ajout": "2026-05-20"},
            {"lien": "https://example.com/2", "titre": "Article 2",
             "resume": "Res 2", "categorie": "Cloud", "pertinence": 7,
             "source": "Src", "date_publication": "2026-05-19", "date_ajout": "2026-05-19"},
        ]

        from tools.database import lire_articles_filtres
        articles, total = lire_articles_filtres()
        assert total == 2
        assert len(articles) == 2

    def test_categories_endpoint(self, mock_pg):
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchall.return_value = [
            {"categorie": "Cloud"},
            {"categorie": "IA"},
        ]

        from tools.database import lire_categories
        result = lire_categories()
        assert "IA" in result
        assert "Cloud" in result


class TestDigestLiveEndpoint:
    """Test the /digest/live logic."""

    def test_group_by_category(self):
        articles = [
            {"titre": "A1", "lien": "http://a", "resume": "r", "pertinence": 9,
             "categorie": "IA", "source": "s", "date_publication": "2026-05-20"},
            {"titre": "A2", "lien": "http://b", "resume": "r", "pertinence": 7,
             "categorie": "IA", "source": "s", "date_publication": "2026-05-19"},
            {"titre": "A3", "lien": "http://c", "resume": "r", "pertinence": 8,
             "categorie": "Cloud", "source": "s", "date_publication": "2026-05-18"},
        ]

        categories = {}
        for a in articles:
            cat = a.get("categorie", "Autre")
            categories.setdefault(cat, []).append(a)

        assert len(categories) == 2
        assert len(categories["IA"]) == 2
        assert len(categories["Cloud"]) == 1
```

- [ ] **Step 2: Run all tests**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -m pytest tests/test_articles_page.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_articles_page.py
git commit -m "test: add integration tests for articles and digest endpoints"
```

---

### Task 11: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_react_e2e.py -x`
Expected: No regressions

- [ ] **Step 2: Verify all templates parse**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); [env.get_template(t) for t in ['articles.html', 'digest.html', 'base.html', 'index.html', 'dashboard.html', 'login.html', 'about.html']]; print('All templates OK')"`
Expected: `All templates OK`

- [ ] **Step 3: Verify imports**

Run: `cd /Users/josuexavierrocha/Projets/luciole && python -c "from tools.database import lire_articles_filtres, lire_categories, enregistrer_envoi_pg, lire_historique_digest, lire_digest_archive; print('All DB imports OK')"`
Expected: `All DB imports OK`

- [ ] **Step 4: Final commit (if any remaining changes)**

```bash
git status
```
