"""
Exercice M5E1 — Tests unitaires des tools de l'agent.
3 types de tests par tool : cas nominal, cas vide, cas d'erreur.
"""
import pytest
from tools.database import query_db


# -------------------------------------------------------------------------
# Test 1 — Client existant trouve
# -------------------------------------------------------------------------
def test_client_existant():
    """query_db retourne le bon client quand il existe."""
    result = query_db("SELECT * FROM clients WHERE nom = 'Alice Martin'")
    assert len(result) == 1
    assert result[0]["nom"] == "Alice Martin"
    assert result[0]["type"] == "Premium"
    assert result[0]["email"] == "alice.martin@example.com"


# -------------------------------------------------------------------------
# Test 2 — Client inexistant retourne vide
# -------------------------------------------------------------------------
def test_client_inexistant():
    """query_db retourne une liste vide pour un client qui n'existe pas."""
    result = query_db("SELECT * FROM clients WHERE nom = 'Fantome Inexistant'")
    assert isinstance(result, list)
    assert len(result) == 0


# -------------------------------------------------------------------------
# Test 3 — Requete SQL invalide ne crash pas (leve ValueError)
# -------------------------------------------------------------------------
def test_sql_invalide_non_select():
    """query_db refuse les requetes non-SELECT avec une ValueError."""
    with pytest.raises(ValueError):
        query_db("DELETE FROM clients WHERE id = 1")


def test_sql_invalide_update():
    """query_db refuse les UPDATE."""
    with pytest.raises(ValueError):
        query_db("UPDATE clients SET nom = 'Hack' WHERE id = 1")


# -------------------------------------------------------------------------
# Tests supplementaires — couverture etendue
# -------------------------------------------------------------------------
def test_select_tous_les_clients():
    """query_db retourne les 3 clients fictifs de la base de test."""
    result = query_db("SELECT * FROM clients")
    assert len(result) == 3


def test_filtre_par_type_premium():
    """query_db filtre correctement par type Premium."""
    result = query_db("SELECT * FROM clients WHERE type = 'Premium'")
    assert len(result) == 2
    for client in result:
        assert client["type"] == "Premium"


def test_sql_syntaxe_invalide():
    """query_db leve RuntimeError sur une requete SQL mal formee."""
    with pytest.raises(RuntimeError):
        query_db("SELECT * FROM table_inexistante")


def test_colonnes_retournees():
    """query_db retourne des dicts avec les bonnes cles."""
    result = query_db("SELECT nom, email FROM clients LIMIT 1")
    assert len(result) == 1
    assert "nom" in result[0]
    assert "email" in result[0]
