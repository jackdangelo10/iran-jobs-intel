# src/database/connection.py
"""
PostgreSQL database connection manager using psycopg3.
Handles connection pooling for efficient database access.
"""
from __future__ import annotations
import psycopg
from psycopg.rows import dict_row, DictRow
from psycopg_pool import ConnectionPool
import threading
from typing import Any, LiteralString, cast
from src.config.settings import settings


class DatabaseConnection:
    """
    Thread-safe PostgreSQL connection manager with connection pooling.
    
    Uses psycopg3 with connection pooling for efficient resource usage.
    Configured for use with Supabase PostgreSQL.
    """

    def __init__(self, conninfo: str | None = None):
        """
        Initialize database connection pool.
        
        Args:
            conninfo: PostgreSQL connection string. If None, uses settings.database_url
                     Format: postgresql://user:password@host:port/database
        """
        self.conninfo = conninfo or settings.database_url
        
        if not self.conninfo:
            raise ValueError(
                "Database connection string not provided. "
                "Set IRAN_JOBS_DATABASE_URL in .env or provide conninfo parameter."
            )
        
        # Connection pool for efficient connection reuse
        # min_size=1, max_size=10 is good for Cloud Run Jobs (single instance)
        self.pool: ConnectionPool[psycopg.Connection[DictRow]] = ConnectionPool(
            conninfo=self.conninfo,
            min_size=1,
            max_size=10,
            kwargs={'row_factory': dict_row}  # Return results as dicts by default
        )
        
        # Thread-local storage (Cloud Run is single-threaded, but keep for safety)
        self.local = threading.local()
        
        print(f"✅ Database connection pool initialized (min=1, max=10)")

    def get_connection(self) -> psycopg.Connection[DictRow]:
        """
        Get a connection from the pool.
        
        Returns:
            psycopg.Connection with DictRow factory (results as dicts)
        """
        conn = self.pool.getconn()
        return conn

    def return_connection(self, conn: psycopg.Connection[DictRow]) -> None:
        """
        Return a connection to the pool.
        
        Args:
            conn: Connection to return
        """
        self.pool.putconn(conn)

    def close_connection(self):
        """Close the connection pool and release all connections."""
        if hasattr(self, 'pool') and self.pool:
            self.pool.close()
            print("✅ Database connection pool closed")

    @staticmethod
    def _to_literal(sql: str) -> LiteralString:
        """
        Cast a string to LiteralString for type checking.
        
        This is safe because our SQL queries are defined in code, not from user input.
        Use this helper to satisfy psycopg3's type requirements.
        """
        return cast(LiteralString, sql)

    def execute_with_transaction(
        self, 
        sql: str, 
        parameters: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        """
        Execute a query within a transaction (auto-commit on success, rollback on error).
        
        Args:
            sql: SQL query to execute
            parameters: Query parameters (tuple for positional, dict for named)
            
        Raises:
            Exception: If query execution fails
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(self._to_literal(sql), parameters)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)

    def execute_insert_with_id(
        self, 
        sql: str, 
        parameters: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> int:
        """
        Execute an INSERT statement and return the last inserted row ID.
        
        Important: Your INSERT query MUST include "RETURNING id" at the end.
        Example: INSERT INTO table (col1) VALUES (%s) RETURNING id
        
        Args:
            sql: INSERT SQL query with RETURNING id clause
            parameters: Query parameters
            
        Returns:
            int: ID of the inserted row
            
        Raises:
            Exception: If insert fails or no ID returned
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(self._to_literal(sql), parameters)
                conn.commit()
                
                # Fetch the returned ID
                result = cursor.fetchone()
                
                if result is None:
                    raise Exception(
                        "Failed to get insert ID - query must include 'RETURNING id' clause"
                    )
                
                # Result is a DictRow (dict-like)
                return int(result['id'])
                    
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)

    def fetchone(
        self, 
        sql: str, 
        parameters: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Fetch a single row.
        
        Args:
            sql: SELECT query
            parameters: Query parameters
            
        Returns:
            Dict representing the row, or None if no results
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(self._to_literal(sql), parameters)
                result = cursor.fetchone()
                # Convert DictRow to regular dict for type compatibility
                return dict(result) if result else None
        finally:
            self.return_connection(conn)

    def fetchall(
        self, 
        sql: str, 
        parameters: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch all rows.
        
        Args:
            sql: SELECT query
            parameters: Query parameters
            
        Returns:
            List of dicts representing rows
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(self._to_literal(sql), parameters)
                results = cursor.fetchall()
                # Convert DictRows to regular dicts for type compatibility
                return [dict(row) for row in results]
        finally:
            self.return_connection(conn)