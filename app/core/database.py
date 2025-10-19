import os
import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor


Params = Union[Tuple[Any, ...], List[Any], Dict[str, Any], None]


class Database:
    """
    Wrapper simples para PostgreSQL com pool de conexões e utilitários de consulta.
    - Usa ThreadedConnectionPool
    - Métodos: execute, fetchone, fetchall, fetchval
    - transaction() para blocos atômicos
    - Opção de cursor em dict (RealDictCursor)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        minconn: int = 1,
        maxconn: int = 10,
        use_dict_cursor: bool = True,
    ):
        self.host = host or os.getenv("PGHOST", "localhost")
        self.port = port or int(os.getenv("PGPORT", "5432"))
        self.database = database or os.getenv("PGDATABASE", "postgres")
        self.user = user or os.getenv("PGUSER", "postgres")
        self.password = password or os.getenv("PGPASSWORD", "")

        self.use_dict_cursor = use_dict_cursor

        self._pool: pool.ThreadedConnectionPool = psycopg2.pool.ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )
        print("PostgreSQL pool criado (%s:%s/%s)", self.host, self.port, self.database)

    def _cursor_factory(self):
        return RealDictCursor if self.use_dict_cursor else None

    @contextmanager
    def _get_conn_cursor(self):
        conn = self._pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=self._cursor_factory())
            try:
                yield conn, cur
            finally:
                cur.close()
        finally:
            self._pool.putconn(conn)

    def execute(self, sql: str, params: Params = None) -> int:
        """
        Executa DML (INSERT/UPDATE/DELETE) com commit automático.
        Retorna rowcount.
        """
        with self._get_conn_cursor() as (conn, cur):
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount

    def fetchone(self, sql: str, params: Params = None):
        """
        Executa SELECT e retorna uma linha (ou None).
        """
        with self._get_conn_cursor() as (_, cur):
            cur.execute(sql, params)
            return cur.fetchone()

    def fetchall(self, sql: str, params: Params = None) -> List[Any]:
        """
        Executa SELECT e retorna todas as linhas (lista).
        """
        with self._get_conn_cursor() as (_, cur):
            cur.execute(sql, params)
            return cur.fetchall()

    def fetchval(self, sql: str, params: Params = None) -> Any:
        """
        Executa SELECT e retorna o primeiro valor da primeira linha (ou None).
        """
        row = self.fetchone(sql, params)
        if row is None:
            return None
        if self.use_dict_cursor:
            # RealDictCursor → dict: pegue o primeiro valor
            return next(iter(row.values())) if row else None
        # cursor normal → tupla
        return row[0] if row else None

    @contextmanager
    def transaction(self):
        """
        Uso:
        with db.transaction() as cur:
            cur.execute("...")
            cur.execute("...")
        # commit automático; rollback em exceção
        """
        conn = self._pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=self._cursor_factory())
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
        finally:
            self._pool.putconn(conn)

    def healthcheck(self) -> bool:
        try:
            return self.fetchval("SELECT 1") == 1
        except Exception as e:
            print(f"Healthcheck falhou: {e}")
            return False

    def close(self):
        if self._pool:
            self._pool.closeall()
            print("Pool fechado")
