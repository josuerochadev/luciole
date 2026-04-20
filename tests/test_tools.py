"""
Exercice M5E1 — Tests unitaires des tools de l'agent.
3 types de tests par tool : cas nominal, cas vide, cas d'erreur.

Couverture :
  - database.py  : query_db, charger/sauvegarder JSON, articles, archives, logs
  - search.py    : search_web, filtrer_par_theme
  - email.py     : generer_html, generer_texte, _etoiles, _badge
  - rag.py       : _score_fraicheur, _article_id, index persistence
  - transcribe.py: validation fichier/format
  - vision.py    : validation fichier/format
"""
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest


# =========================================================================
# 1. DATABASE — query_db
# =========================================================================

from tools.database import query_db


class TestQueryDb:
    """Tests de query_db sur la base SQLite de test."""

    def test_client_existant(self):
        result = query_db("SELECT * FROM clients WHERE nom = 'Alice Martin'")
        assert len(result) == 1
        assert result[0]["nom"] == "Alice Martin"
        assert result[0]["type"] == "Premium"

    def test_client_inexistant(self):
        result = query_db("SELECT * FROM clients WHERE nom = 'Fantome'")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_select_tous(self):
        result = query_db("SELECT * FROM clients")
        assert len(result) == 3

    def test_filtre_premium(self):
        result = query_db("SELECT * FROM clients WHERE type = 'Premium'")
        assert len(result) == 2
        assert all(c["type"] == "Premium" for c in result)

    def test_colonnes_retournees(self):
        result = query_db("SELECT nom, email FROM clients LIMIT 1")
        assert "nom" in result[0]
        assert "email" in result[0]

    def test_refuse_delete(self):
        with pytest.raises(ValueError):
            query_db("DELETE FROM clients WHERE id = 1")

    def test_refuse_update(self):
        with pytest.raises(ValueError):
            query_db("UPDATE clients SET nom = 'Hack' WHERE id = 1")

    def test_sql_syntaxe_invalide(self):
        with pytest.raises(RuntimeError):
            query_db("SELECT * FROM table_inexistante")


# =========================================================================
# 2. DATABASE — charger/sauvegarder JSON, articles, archives, logs
# =========================================================================

from tools.database import (
    charger_json,
    sauvegarder_json,
    article_deja_traite,
    sauvegarder_articles,
    enregistrer_envoi,
    archiver_articles_traites,
    ajouter_log,
)


class TestChargerSauvegarderJson:
    """Tests de la couche persistence JSON."""

    def test_charger_fichier_absent(self, data_dir):
        result = charger_json(str(data_dir / "inexistant.json"))
        assert result == []

    def test_sauvegarder_et_recharger(self, data_dir):
        chemin = str(data_dir / "test.json")
        donnees = [{"a": 1}, {"b": 2}]
        sauvegarder_json(chemin, donnees)
        result = charger_json(chemin)
        assert result == donnees

    def test_sauvegarder_unicode(self, data_dir):
        chemin = str(data_dir / "unicode.json")
        sauvegarder_json(chemin, [{"texte": "éàü — ★"}])
        result = charger_json(chemin)
        assert result[0]["texte"] == "éàü — ★"


class TestArticles:
    """Tests de gestion des articles (ajout, déduplication, archivage) — SQLite."""

    def _count_articles(self, data_dir, archive=0):
        """Helper : compte les articles dans SQLite."""
        import sqlite3
        db_path = str(data_dir / "articles.db")
        conn = sqlite3.connect(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE archive = ?", (archive,)
        ).fetchone()[0]
        conn.close()
        return count

    def _get_articles(self, data_dir, archive=0):
        """Helper : récupère les articles depuis SQLite."""
        import sqlite3
        db_path = str(data_dir / "articles.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM articles WHERE archive = ?", (archive,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def test_sauvegarder_nouveaux_articles(self, data_dir, sample_articles):
        with patch("tools.rag.indexer_articles", return_value=2):
            nb = sauvegarder_articles(sample_articles[:2])
        assert nb == 2
        assert self._count_articles(data_dir, archive=0) == 2

    def test_deduplication(self, data_dir, sample_articles):
        with patch("tools.rag.indexer_articles", return_value=1):
            sauvegarder_articles(sample_articles[:1])
            nb = sauvegarder_articles(sample_articles[:1])  # doublon
        assert nb == 0

    def test_article_deja_traite(self, data_dir, sample_articles):
        with patch("tools.rag.indexer_articles", return_value=1):
            sauvegarder_articles(sample_articles[:1])
        assert article_deja_traite("https://example.com/gpt5") is True
        assert article_deja_traite("https://example.com/inconnu") is False

    def test_archiver_articles(self, data_dir, sample_articles):
        with patch("tools.rag.indexer_articles", return_value=2):
            sauvegarder_articles(sample_articles[:2])
        archiver_articles_traites(sample_articles[:1])  # archiver GPT-5
        actifs = self._get_articles(data_dir, archive=0)
        archives = self._get_articles(data_dir, archive=1)
        assert len(actifs) == 1
        assert len(archives) == 1
        assert archives[0]["lien"] == "https://example.com/gpt5"

    def test_archiver_liste_vide(self, data_dir, sample_articles):
        with patch("tools.rag.indexer_articles", return_value=2):
            sauvegarder_articles(sample_articles[:2])
        archiver_articles_traites([])
        assert self._count_articles(data_dir, archive=0) == 2


class TestHistoriqueEtLogs:
    """Tests d'enregistrement d'envoi et de logs."""

    def test_enregistrer_envoi(self, data_dir):
        enregistrer_envoi(["a@b.com"], 5)
        hist = charger_json(str(data_dir / "historique_envois.json"))
        assert len(hist) == 1
        assert hist[0]["nb_articles"] == 5
        assert "date" in hist[0]

    def test_enregistrer_plusieurs_envois(self, data_dir):
        enregistrer_envoi(["a@b.com"], 3)
        enregistrer_envoi(["c@d.com"], 7)
        hist = charger_json(str(data_dir / "historique_envois.json"))
        assert len(hist) == 2

    def test_ajouter_log(self, data_dir):
        ajouter_log("INFO", "Test log", {"source": "pytest"})
        with open(str(data_dir / "logs.jsonl"), "r") as f:
            ligne = json.loads(f.readline())
        assert ligne["niveau"] == "INFO"
        assert ligne["message"] == "Test log"
        assert ligne["source"] == "pytest"

    def test_ajouter_plusieurs_logs(self, data_dir):
        ajouter_log("INFO", "Premier")
        ajouter_log("ERROR", "Deuxième")
        with open(str(data_dir / "logs.jsonl"), "r") as f:
            lignes = f.readlines()
        assert len(lignes) == 2


# =========================================================================
# 3. SEARCH — search_web, filtrer_par_theme
# =========================================================================

from tools.search import search_web, filtrer_par_theme


class TestSearchWeb:
    """Tests de search_web (banque de résultats simulés)."""

    def test_mot_cle_ia(self):
        results = search_web("dernières avancées en IA")
        assert len(results) >= 1
        assert all("titre" in r and "url" in r and "extrait" in r for r in results)

    def test_mot_cle_cloud(self):
        results = search_web("migration cloud AWS")
        assert len(results) >= 1
        assert any("cloud" in r["titre"].lower() or "aws" in r["extrait"].lower() for r in results)

    def test_mot_cle_cybersecurite(self):
        results = search_web("faille cybersécurité")
        assert len(results) >= 1

    def test_mot_cle_gpu(self):
        results = search_web("nouveau GPU nvidia")
        assert len(results) >= 1

    def test_requete_sans_tavily_retourne_liste_vide(self):
        """Sans clé Tavily, search_web retourne une liste vide (pas de résultats fictifs)."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TAVILY_API_KEY", None)
            results = search_web("recette de tarte aux pommes")
        assert results == []

    def test_retour_structure(self):
        """Chaque résultat a les 3 clés attendues (si Tavily est configuré)."""
        results = search_web("IA")
        for r in results:
            assert set(r.keys()) == {"titre", "url", "extrait"}


class TestFiltrerParTheme:
    """Tests de filtrer_par_theme."""

    def test_filtre_articles_pertinents(self, sample_articles):
        result = filtrer_par_theme(sample_articles, ["kubernetes", "cloud"])
        assert len(result) == 1
        assert result[0]["titre"] == "Kubernetes 1.32 disponible"

    def test_filtre_ia(self, sample_articles):
        result = filtrer_par_theme(sample_articles, ["intelligence artificielle", "GPT"])
        assert len(result) >= 1

    def test_filtre_aucun_match(self, sample_articles):
        result = filtrer_par_theme(sample_articles, ["blockchain", "web3"])
        assert len(result) == 0

    def test_filtre_case_insensitive(self):
        articles = [{"titre": "KUBERNETES en prod", "resume_brut": ""}]
        result = filtrer_par_theme(articles, ["kubernetes"])
        assert len(result) == 1

    def test_filtre_liste_vide(self):
        result = filtrer_par_theme([], ["IA"])
        assert result == []


# =========================================================================
# 4. EMAIL — génération HTML/texte, helpers
# =========================================================================

from tools.email import generer_html, generer_texte, _etoiles, _badge


class TestEmailHelpers:
    """Tests des fonctions utilitaires email."""

    def test_etoiles_max(self):
        assert _etoiles(10) == "★★★★★"

    def test_etoiles_zero(self):
        assert _etoiles(0) == "☆☆☆☆☆"

    def test_etoiles_milieu(self):
        result = _etoiles(6)
        assert "★" in result and "☆" in result

    def test_etoiles_negatif(self):
        """Valeur négative clampée à 0."""
        assert _etoiles(-5) == "☆☆☆☆☆"

    def test_badge_ia(self):
        html = _badge("IA")
        assert "IA" in html
        assert "background:" in html

    def test_badge_categorie_inconnue(self):
        html = _badge("Robotique")
        assert "Robotique" in html
        assert "#64748b" in html  # couleur par défaut


class TestGenererHtml:
    """Tests de génération du rapport HTML."""

    def test_html_contient_articles(self, sample_articles):
        html = generer_html(sample_articles[:2], "15/04/2026")
        assert "GPT-5" in html
        assert "Kubernetes" in html
        assert "15/04/2026" in html

    def test_html_structure(self, sample_articles):
        html = generer_html(sample_articles[:1])
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "Veille Technologique" in html

    def test_html_liste_vide(self):
        html = generer_html([])
        assert "0 article" in html

    def test_html_exclut_pas_hors_sujet(self, sample_articles):
        """generer_html ne filtre pas — c'est selectionner_articles qui le fait."""
        html = generer_html(sample_articles)  # inclut le hors-sujet
        assert "cookies" in html.lower()


class TestGenererTexte:
    """Tests de génération du rapport texte brut."""

    def test_texte_contient_articles(self, sample_articles):
        texte = generer_texte(sample_articles[:2], "15/04/2026")
        assert "GPT-5" in texte
        assert "Kubernetes" in texte
        assert "15/04/2026" in texte

    def test_texte_format(self, sample_articles):
        texte = generer_texte(sample_articles[:1])
        assert "RAPPORT DE VEILLE" in texte
        assert "[IA]" in texte

    def test_texte_liste_vide(self):
        texte = generer_texte([])
        assert "RAPPORT" in texte


# =========================================================================
# 5. RAG — fonctions utilitaires (sans appel API)
# =========================================================================

from tools.rag import _score_fraicheur, _article_id, taille_index, vider_index


class TestRagUtils:
    """Tests des utilitaires RAG sans appel OpenAI."""

    def test_score_fraicheur_aujourdhui(self):
        now = datetime.now(timezone.utc).isoformat()
        score = _score_fraicheur(now)
        assert 0.9 <= score <= 1.0

    def test_score_fraicheur_vieux(self):
        vieux = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        score = _score_fraicheur(vieux)
        assert score == 0.0

    def test_score_fraicheur_date_vide(self):
        assert _score_fraicheur("") == 0.5

    def test_score_fraicheur_date_invalide(self):
        assert _score_fraicheur("pas-une-date") == 0.5

    def test_article_id_deterministe(self):
        id1 = _article_id("https://example.com/article1")
        id2 = _article_id("https://example.com/article1")
        assert id1 == id2
        assert len(id1) == 16

    def test_article_id_unique(self):
        id1 = _article_id("https://example.com/a")
        id2 = _article_id("https://example.com/b")
        assert id1 != id2

    def test_index_vide_par_defaut(self, data_dir):
        """Un index fraîchement créé a une taille de 0."""
        # Patcher EMBEDDINGS_FILE pour utiliser le tmp_path
        import tools.rag as rag_mod
        original = rag_mod.EMBEDDINGS_FILE
        rag_mod.EMBEDDINGS_FILE = str(data_dir / "embeddings.json")
        try:
            assert taille_index() == 0
        finally:
            rag_mod.EMBEDDINGS_FILE = original

    def test_vider_index(self, data_dir):
        import tools.rag as rag_mod
        original = rag_mod.EMBEDDINGS_FILE
        rag_mod.EMBEDDINGS_FILE = str(data_dir / "embeddings.json")
        try:
            # Écrire un faux index
            with open(rag_mod.EMBEDDINGS_FILE, "w") as f:
                json.dump([{"id": "fake", "embedding": [0.1]}], f)
            assert taille_index() == 1
            vider_index()
            assert taille_index() == 0
        finally:
            rag_mod.EMBEDDINGS_FILE = original


# =========================================================================
# 6. TRANSCRIBE — validation (sans appel API)
# =========================================================================

from tools.transcribe import transcrire_audio


class TestTranscribeValidation:
    """Tests de validation avant appel API Whisper."""

    def test_fichier_inexistant(self):
        with pytest.raises(FileNotFoundError, match="introuvable"):
            transcrire_audio("/tmp/fichier_qui_nexiste_pas.mp3")

    def test_format_non_supporte(self, tmp_path):
        fake = tmp_path / "test.txt"
        fake.write_text("pas de l'audio")
        with pytest.raises(ValueError, match="non supporté"):
            transcrire_audio(str(fake))

    def test_format_supporte_mais_pas_de_cle(self, tmp_path):
        """Un .mp3 existant passe la validation mais échoue à l'appel API."""
        fake = tmp_path / "test.mp3"
        fake.write_bytes(b"\x00" * 100)
        with pytest.raises(RuntimeError):
            transcrire_audio(str(fake))


# =========================================================================
# 7. VISION — validation (sans appel API)
# =========================================================================

from tools.vision import analyser_image


class TestVisionValidation:
    """Tests de validation avant appel API GPT-4o Vision."""

    def test_fichier_inexistant(self):
        with pytest.raises(FileNotFoundError, match="introuvable"):
            analyser_image("/tmp/image_qui_nexiste_pas.png")

    def test_format_non_supporte(self, tmp_path):
        fake = tmp_path / "test.bmp"
        fake.write_bytes(b"\x00" * 100)
        with pytest.raises(ValueError, match="non supporté"):
            analyser_image(str(fake))

    def test_format_jpg_passe_validation(self, tmp_path):
        """Un .jpg existant passe la validation mais échoue à l'appel API."""
        fake = tmp_path / "test.jpg"
        fake.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        with pytest.raises((RuntimeError, Exception)):
            analyser_image(str(fake))
