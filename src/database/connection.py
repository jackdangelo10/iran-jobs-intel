# database/connection.py
from __future__ import annotations
from typing import Optional, Sequence, Any, Union, Dict
import sqlite3
import threading



class DatabaseConnection:

    def __init__(self, db_path: str = "data/databases/iran_jobs.db"):
        if not isinstance(db_path, str):
            raise TypeError("Expected dp_path as string.")
        self.db_path = db_path
        self.local = threading.local()

    def get_connection(self):

        conn = getattr(self.local, 'connection', None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            self.local.connection = conn
        return conn

    def close_connection(self):
        conn = getattr(self.local, 'connection', None)

        if not isinstance(conn, sqlite3.Connection):
            self.local.connection = None
            conn = None
        
        if conn is not None:
            conn.close()
            self.local.connection = None

    def execute_with_transaction(self, sql : str, parameters: Optional[Union[Sequence[Any], Dict[str, Any]]] = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if parameters is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, parameters)
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    