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
