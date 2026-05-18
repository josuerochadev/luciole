# Contribuer à Luciole

## Prérequis

- Python 3.12+
- Compte Neon (PostgreSQL gratuit)
- Clé API Google Gemini (Google AI Studio, gratuit)

## Installation dev

```bash
git clone https://github.com/josuerochadev/luciole.git
cd luciole
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Renseigner GEMINI_API_KEY, DATABASE_URL, API_KEY, JWT_SECRET
python startup.py   # initialise la base + importe les premiers articles
```

## Workflow

1. Créer une branche depuis `main` : `git checkout -b feat/ma-feature`
2. Coder, tester, commiter
3. Ouvrir une PR vers `main`

**Règles PR :**
- Une PR = un thème (pas de PR fourre-tout)
- Tous les tests doivent passer : `python -m pytest tests/ -v`
- Validation visuelle manuelle sur mobile / tablette / desktop avant merge (pour les changements frontend)

## Commits

Format [Conventional Commits](https://www.conventionalcommits.org/) obligatoire :

```
feat: ajouter le support multi-langue
fix: corriger le score RAG pour les articles sans date
docs: mettre à jour ARCHITECTURE.md
chore: mettre à jour les dépendances
refactor: extraire la logique d'embedding dans un module dédié
test: ajouter les tests de l'endpoint /upload
```

Ne jamais bypasser les hooks pre-commit (`--no-verify` interdit).

## Tests

```bash
# Suite complète
python -m pytest tests/ -v

# Un fichier
python -m pytest tests/test_security.py -v

# Avec couverture
python -m pytest tests/ --cov=. --cov-report=term-missing
```

Les tests nécessitent les variables d'environnement du `.env`. Pour les tests unitaires
sans base de données, les fixtures mockent les connexions PostgreSQL.

## Structure du projet

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour le détail des modules.
Les décisions architecturales majeures sont documentées dans [docs/adr/](docs/adr/).

## Variables d'environnement

Voir `.env.example` pour la liste complète avec descriptions.
