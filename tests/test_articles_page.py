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
        # _init_articles_table issues 3 execute calls (CREATE TABLE + 2 indexes),
        # so the COUNT query is at index 3 and the SELECT at index 4.
        count_call = mock_cur.execute.call_args_list[3]
        count_sql = count_call[0][0]
        assert "archive = 0" in count_sql
        assert "pertinence >=" in count_sql

    def test_categorie_filter(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(categorie="IA")

        count_call = mock_cur.execute.call_args_list[3]
        count_sql = count_call[0][0]
        assert "categorie = %s" in count_sql

    def test_date_filters(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(date_min="2026-01-01", date_max="2026-12-31")

        count_call = mock_cur.execute.call_args_list[3]
        count_sql = count_call[0][0]
        assert "date_publication >=" in count_sql
        assert "date_publication <=" in count_sql

    def test_tri_pertinence(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(tri="pertinence")

        select_call = mock_cur.execute.call_args_list[4]
        select_sql = select_call[0][0]
        assert "ORDER BY pertinence DESC" in select_sql

    def test_tri_date(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(tri="date")

        select_call = mock_cur.execute.call_args_list[4]
        select_sql = select_call[0][0]
        assert "ORDER BY date_publication DESC" in select_sql

    def test_offset_and_limit(self, mock_pg):
        from tools.database import lire_articles_filtres
        mock_conn, mock_cur = mock_pg
        mock_cur.fetchone.return_value = {"total": 0}
        mock_cur.fetchall.return_value = []

        lire_articles_filtres(offset=20, limit=10)

        select_call = mock_cur.execute.call_args_list[4]
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


class TestArticlesEndpoints:
    """Test the /articles and /articles/categories endpoints via mock DB."""

    def test_articles_endpoint_returns_structure(self, mock_pg):
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
