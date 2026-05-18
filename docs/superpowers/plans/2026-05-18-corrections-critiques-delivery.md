# Corrections Critiques Delivery & Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mettre en place les trois garde-fous manquants identifiés dans l'audit C1/C2/C3 : `.gitignore`, pre-commit hooks actifs, pipeline CI/CD GitHub Actions.

**Architecture:** Trois tâches indépendantes à exécuter dans l'ordre. C1 d'abord (protège les secrets avant tout), puis C2 (valide la qualité localement), puis C3 (valide en ligne à chaque push). Aucune modification du code applicatif — uniquement de l'infrastructure de développement.

**Tech Stack:** Git, pre-commit 4.x, pre-commit-hooks v5, ruff v0.9.x, GitHub Actions (ubuntu-latest, python 3.12), pytest

---

## Fichiers concernés

| Action | Fichier |
|--------|---------|
| Créer | `.gitignore` |
| Créer | `.pre-commit-config.yaml` |
| Créer | `.github/workflows/ci.yml` |

---

## Task 1 : Créer `.gitignore` (C1 — risque de leak secrets)

**Fichiers :**
- Créer : `.gitignore`

**Contexte :** Sans `.gitignore`, un `git add .` committerait `.env` (GEMINI_API_KEY, JWT_SECRET, DATABASE_URL), `.venv/`, `__pycache__/`, `data/` et `chroma_db/`. Le `.env` est actuellement listé comme `??` (untracked) dans `git status` — la seule protection est l'absence d'ajout manuel.

- [ ] **Step 1 : Vérifier l'état actuel avant la création**

```bash
git status
```

Résultat attendu : `.env`, `__pycache__/`, `agent/__pycache__/`, etc. listés comme `??` (untracked non ignorés).

- [ ] **Step 2 : Créer `.gitignore`**

Créer `/Users/josuexavierrocha/Projets/luciole/.gitignore` avec ce contenu exact :

```gitignore
# Secrets — ne JAMAIS committer
.env
*.key
*.pem

# Environnement virtuel Python
.venv/
venv/
env/

# Bytecode Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Données éphémères (reconstructibles depuis Neon)
data/
chroma_db/
chromadb_data/

# Artefacts de test et couverture
.pytest_cache/
.coverage
htmlcov/
coverage.xml

# Artefacts de build
*.egg-info/
dist/
build/
*.egg

# IDE
.idea/
.vscode/
*.swp
*.swo

# macOS
.DS_Store

# Logs
*.log
```

- [ ] **Step 3 : Vérifier que les fichiers sensibles sont maintenant ignorés**

```bash
git status
```

Résultat attendu : `.env` N'APPARAIT PLUS dans la sortie. Les `__pycache__/` également absents.

- [ ] **Step 4 : Vérifier qu'aucun fichier sensible n'est déjà tracké par erreur**

```bash
git ls-files --cached | grep -E "\.env$|\.key$|__pycache__"
```

Résultat attendu : aucune sortie. Si des fichiers apparaissent, les désindexer avec `git rm --cached <fichier>` AVANT de committer.

- [ ] **Step 5 : Committer**

```bash
git add .gitignore
git commit -m "chore: add .gitignore — protects secrets and ephemeral files"
```

---

## Task 2 : Configurer les pre-commit hooks (C2 — aucun hook actif)

**Fichiers :**
- Créer : `.pre-commit-config.yaml`

**Contexte :** Tous les hooks dans `.git/hooks/` sont des `.sample` (inactifs). CONTRIBUTING.md interdit `--no-verify` mais rien ne tourne. On installe `pre-commit` et on configure 2 niveaux de vérification : sécurité (detect-private-key) et qualité (ruff, trailing whitespace).

- [ ] **Step 1 : Installer pre-commit**

```bash
pip install pre-commit
pre-commit --version
```

Résultat attendu : `pre-commit 4.x.x`

- [ ] **Step 2 : Créer `.pre-commit-config.yaml`**

Créer `/Users/josuexavierrocha/Projets/luciole/.pre-commit-config.yaml` :

```yaml
repos:
  # Hooks standards — sécurité et qualité basique
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: detect-private-key        # bloque les clés privées et tokens
      - id: check-added-large-files   # bloque les fichiers > 500 KB
        args: ['--maxkb=500']
      - id: check-merge-conflict      # détecte les marqueurs de conflit non résolus
      - id: check-yaml                # valide la syntaxe YAML
      - id: check-json                # valide la syntaxe JSON
      - id: trailing-whitespace       # supprime les espaces en fin de ligne
      - id: end-of-file-fixer         # s'assure que les fichiers finissent par \n
      - id: mixed-line-ending         # normalise LF/CRLF
        args: ['--fix=lf']

  # Linter Python — ruff (rapide, remplace flake8/isort/pyupgrade)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.6
    hooks:
      - id: ruff                      # lint + autofix des erreurs simples
        args: [--fix, --exit-non-zero-on-fix]
        types_or: [python, pyi]
```

**Note sur ruff :** `--exit-non-zero-on-fix` fait échouer le commit si ruff a dû corriger des fichiers (pour forcer un re-`git add` conscient). Les corrections sont appliquées automatiquement — il suffit de re-stager et recommitter.

- [ ] **Step 3 : Installer les hooks dans le dépôt local**

```bash
cd /Users/josuexavierrocha/Projets/luciole && pre-commit install
```

Résultat attendu :
```
pre-commit installed at .git/hooks/pre-commit
```

- [ ] **Step 4 : Télécharger les environnements des hooks (une seule fois)**

```bash
pre-commit install --install-hooks
```

Résultat attendu : téléchargement des hooks ruff et pre-commit-hooks. Peut prendre 30-60 secondes.

- [ ] **Step 5 : Lancer sur l'ensemble du code existant pour voir les violations**

```bash
cd /Users/josuexavierrocha/Projets/luciole && pre-commit run --all-files
```

Résultat attendu : certaines vérifications passent (check-yaml, check-json, detect-private-key), ruff peut signaler des erreurs sur le code existant. Les corrections ruff sont appliquées automatiquement en place.

- [ ] **Step 6 : Si ruff a modifié des fichiers, les re-stager**

```bash
git diff --stat
git add -p   # ou git add <fichiers modifiés par ruff>
```

- [ ] **Step 7 : Relancer pour confirmer que tout passe**

```bash
pre-commit run --all-files
```

Résultat attendu : `Passed` sur tous les hooks.

- [ ] **Step 8 : Committer**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: add pre-commit hooks — detect-private-key, ruff, yaml/json checks"
```

Le hook pre-commit se déclenchera sur ce commit lui-même — c'est le bon signe.

---

## Task 3 : Créer le pipeline CI GitHub Actions (C3 — aucune CI)

**Fichiers :**
- Créer : `.github/workflows/ci.yml`

**Contexte :** Pas de `.github/` dans le dépôt. Le pipeline cible les tests qui n'ont pas besoin d'API keys réelles : `test_security.py` (pur unitaire) et `test_react_e2e.py` (tout mocké avec `@patch`). Les tests marqués `integration` et `qualite` sont exclus car ils consomment des tokens LLM et nécessitent des secrets.

- [ ] **Step 1 : Créer le répertoire `.github/workflows/`**

```bash
mkdir -p /Users/josuexavierrocha/Projets/luciole/.github/workflows
```

- [ ] **Step 2 : Créer `.github/workflows/ci.yml`**

Créer `/Users/josuexavierrocha/Projets/luciole/.github/workflows/ci.yml` :

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Lint & Unit Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install ruff
        run: pip install ruff

      - name: Lint (ruff)
        run: ruff check . --output-format=github
        continue-on-error: true  # lint ne bloque pas la CI tant que le code n'est pas nettoyé

      - name: Unit tests (sans LLM)
        run: |
          pytest tests/test_security.py tests/test_react_e2e.py \
            -v --tb=short
        env:
          # Valeurs factices pour éviter les erreurs d'import au module level
          GEMINI_API_KEY: "ci-dummy-key"
          DATABASE_URL: "postgresql://ci:ci@localhost/ci"
          API_KEY: "ci-dummy-api-key"
          JWT_SECRET: "ci-dummy-jwt-secret-minimum-32-chars-ok"
          LANGFUSE_PUBLIC_KEY: ""
          LANGFUSE_SECRET_KEY: ""
```

**Pourquoi `continue-on-error: true` sur ruff ?** Le code existant peut avoir des violations ruff héritées. Bloquer la CI immédiatement empêcherait tout merge. Retirer ce flag une fois que `pre-commit run --all-files` passe proprement (après Task 2).

**Pourquoi ces deux fichiers de test ?**
- `test_security.py` : aucune dépendance externe, tests purement sur regex/logique
- `test_react_e2e.py` : tous les appels LLM/DB sont mockés avec `unittest.mock.patch`

- [ ] **Step 3 : Vérifier la syntaxe YAML du workflow**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML valide"
```

Résultat attendu : `YAML valide`

- [ ] **Step 4 : Vérifier que les tests ciblés passent localement**

```bash
cd /Users/josuexavierrocha/Projets/luciole && \
  GEMINI_API_KEY="ci-dummy-key" \
  DATABASE_URL="postgresql://ci:ci@localhost/ci" \
  API_KEY="ci-dummy-api-key" \
  JWT_SECRET="ci-dummy-jwt-secret-minimum-32-chars-ok" \
  pytest tests/test_security.py tests/test_react_e2e.py -v --tb=short
```

Résultat attendu : tous les tests PASSED. Si des tests échouent, investiguer avant de committer.

- [ ] **Step 5 : Committer**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline — lint + unit tests on push/PR"
```

- [ ] **Step 6 : Pousser et vérifier que la CI se déclenche**

```bash
git push origin main
```

Aller sur `https://github.com/josuerochadev/luciole/actions` et vérifier que le workflow `CI` apparaît et passe.

---

## Self-Review

**Couverture des problèmes critiques :**
- C1 (.gitignore) → Task 1 ✓
- C2 (pre-commit hooks) → Task 2 ✓
- C3 (CI/CD) → Task 3 ✓

**Vérifications placeholder :** aucun TBD/TODO dans le plan.

**Cohérence :** les noms de fichiers et commandes sont consistants entre les tâches.

**Limitation connue — tests CI :** seuls `test_security.py` et `test_react_e2e.py` sont dans la CI initiale. `test_tools.py`, `test_memory.py`, `test_agent_debug.py` nécessitent soit un mock PostgreSQL, soit de les marquer `@pytest.mark.integration`. C'est un problème Important (I6 de l'audit), pas Critique — hors scope de ce plan.

**Limitation connue — ruff `continue-on-error` :** intentionnel pour ne pas bloquer la CI sur du code existant non encore nettoyé. À retirer après un passage `pre-commit run --all-files` complet.
