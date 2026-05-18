"""
Helpers PostgreSQL partagés — pool de connexions + curseur RealDict.
Importé par database.py, memory/store.py et tools/database.py.

Le pool (ThreadedConnectionPool) est initialisé une fois par process.
Chaque connect() extrait une connexion du pool ; conn.close() la réintègre.
"""
import threading

import psycopg2
import psycopg2.extras
import psycopg2.pool

from config import DATABASE_URL

_DB_POOL_MIN = 2
_DB_POOL_MAX = 10

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Initialise le pool si nécessaire (lazy, thread-safe)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    _DB_POOL_MIN, _DB_POOL_MAX, DATABASE_URL
                )
    return _pool


class _PooledConn:
    """
    Proxy transparent sur une connexion psycopg2 extraite du pool.
    Tous les attributs/méthodes sont délégués à la connexion réelle ;
    conn.close() réintègre la connexion dans le pool au lieu de la fermer.
    """

    __slots__ = ("_conn", "_pool")

    def __init__(self, conn, pool: psycopg2.pool.ThreadedConnectionPool):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_pool", pool)

    def __getattr__(self, name: str):
        return getattr(object.__getattribute__(self, "_conn"), name)

    def close(self):
        pool = object.__getattribute__(self, "_pool")
        conn = object.__getattribute__(self, "_conn")
        pool.putconn(conn)


def connect() -> _PooledConn:
    """Extrait une connexion du pool (compatible avec l'ancienne signature)."""
    pool = _get_pool()
    return _PooledConn(pool.getconn(), pool)


def cursor(conn) -> psycopg2.extras.RealDictCursor:
    """Retourne un curseur RealDictCursor sur la connexion fournie."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
