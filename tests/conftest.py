"""Configure le sys.path pour que les tests trouvent les modules racine."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def data_dir(tmp_path):
    """Crée un répertoire data temporaire et patche config pour l'utiliser."""
    import config

    original = {
        "DATA_DIR": config.DATA_DIR,
        "ARTICLES_FILE": config.ARTICLES_FILE,
        "HISTORIQUE_FILE": config.HISTORIQUE_FILE,
        "ARCHIVES_FILE": config.ARCHIVES_FILE,
        "LOGS_FILE": config.LOGS_FILE,
    }

    config.DATA_DIR = str(tmp_path)
    config.ARTICLES_FILE = str(tmp_path / "articles.json")
    config.HISTORIQUE_FILE = str(tmp_path / "historique_envois.json")
    config.ARCHIVES_FILE = str(tmp_path / "archives.json")
    config.LOGS_FILE = str(tmp_path / "logs.jsonl")

    # Patcher aussi dans database.py qui importe ces valeurs au top-level
    import tools.database as db_mod
    db_mod.ARTICLES_FILE = config.ARTICLES_FILE
    db_mod.HISTORIQUE_FILE = config.HISTORIQUE_FILE
    db_mod.ARCHIVES_FILE = config.ARCHIVES_FILE
    db_mod.LOGS_FILE = config.LOGS_FILE
    db_mod.DATA_DIR = config.DATA_DIR
    db_mod.DB_TEST_PATH = str(tmp_path / "test_clients.db")

    yield tmp_path

    # Restore
    for k, v in original.items():
        setattr(config, k, v)


@pytest.fixture
def sample_articles():
    """Jeu d'articles fictifs pour les tests."""
    return [
        {
            "titre": "GPT-5 révolutionne le code",
            "lien": "https://example.com/gpt5",
            "resume": "OpenAI lance GPT-5 avec des capacités de raisonnement avancées.",
            "resume_brut": "OpenAI lance GPT-5 avec des capacités de raisonnement avancées.",
            "categorie": "IA",
            "pertinence": 9,
            "date_publication": "2026-04-10T12:00:00+00:00",
            "source": "TechCrunch",
        },
        {
            "titre": "Kubernetes 1.32 disponible",
            "lien": "https://example.com/k8s",
            "resume": "Nouvelle version de Kubernetes avec des améliorations de sécurité.",
            "resume_brut": "Nouvelle version de Kubernetes avec des améliorations de sécurité.",
            "categorie": "Cloud",
            "pertinence": 7,
            "date_publication": "2026-04-08T10:00:00+00:00",
            "source": "KubeBlog",
        },
        {
            "titre": "Recette de cookies maison",
            "lien": "https://example.com/cookies",
            "resume": "Une recette facile pour des cookies moelleux.",
            "resume_brut": "Une recette facile pour des cookies moelleux.",
            "categorie": "Hors-sujet",
            "pertinence": 1,
            "date_publication": "2026-04-01T08:00:00+00:00",
            "source": "CuisineBlog",
        },
    ]
