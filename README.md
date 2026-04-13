# Agent de Veille Technologique

Agent IA automatisé pour la veille technologique, développé dans le cadre d'une formation en Intelligence Artificielle.

## Fonctionnalités

- **Pipeline automatisé** : collecte d'articles RSS, filtrage par thèmes, enrichissement par LLM (résumé, catégorisation, score de pertinence)
- **Agent conversationnel** : interface en langage naturel avec raisonnement ReAct et 4 outils (base de données, recherche web, recherche sémantique, réponse directe)
- **RAG (Retrieval-Augmented Generation)** : recherche sémantique par embeddings avec scoring hybride (similarité cosinus + fraîcheur)
- **Rapports email** : génération de digests HTML stylisés avec envoi SMTP
- **Gouvernance des données** : rétention automatique (90j articles, 30j logs), protection anti-injection SQL, conformité RGPD

## Architecture

```
agent-fil-rouge/
├── main.py              # Agent conversationnel (boucle ReAct)
├── pipeline.py          # Pipeline automatisé RSS → LLM → stockage
├── seed.py              # Peuplement initial de la base d'articles
├── config.py            # Configuration centralisée
├── llm.py               # Interface OpenAI (appels LLM, parsing JSON)
├── tools/
│   ├── search.py        # Collecte RSS + recherche web
│   ├── database.py      # Persistance SQLite + JSON
│   ├── email.py         # Génération et envoi de rapports
│   └── rag.py           # Embeddings + recherche sémantique
├── memory/
│   └── store.py         # Mémoire de session conversationnelle
├── tests/               # Tests unitaires et d'intégration
├── docs/                # Documentation et résultats d'exercices
└── data/                # Données générées (gitignored)
```

## Installation

```bash
# Cloner le repo
# Depuis la racine du repo
cd fil-rouge

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec votre clé OpenAI
```

## Utilisation

### Pipeline de veille (collecte et enrichissement)

```bash
python pipeline.py
```

### Agent conversationnel

```bash
python main.py
```

### Peuplement initial (articles de test)

```bash
python seed.py
```

### Tests

```bash
python -m pytest tests/ -v
```

## Configuration

Les paramètres principaux sont dans `config.py` :
- **Modèle LLM** : `gpt-4o-mini` (température 0.3)
- **Sources RSS** : 12 flux (tech FR/EN, cloud, cybersécurité, IA)
- **Thèmes surveillés** : 18 mots-clés (IA, cloud, DevOps, sécurité...)
- **Seuil de pertinence** : 5/10 minimum

Voir `.env.example` pour les variables d'environnement requises.

## Équipe

Projet réalisé par **Alex Dubus**, **Zhengfeng Ding**, **Josue Xavier Rocha** et **Stéphanie Consoli**.

## Licence

Projet éducatif — usage libre.
