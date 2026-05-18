"""
Helpers PostgreSQL partagés — connexion et curseur RealDict.
Importé par database.py, memory/store.py et tools/database.py.
"""
import psycopg2
import psycopg2.extras

from config import DATABASE_URL


def connect() -> psycopg2.extensions.connection:
    """Ouvre une connexion PostgreSQL à partir de DATABASE_URL."""
    return psycopg2.connect(DATABASE_URL)


def cursor(conn) -> psycopg2.extras.RealDictCursor:
    """Retourne un curseur RealDictCursor sur la connexion fournie."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
