# tests/test_database/test_connection.py
import pytest
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from src.database.connection import DatabaseConnection

class TestDatabaseConnection:

    def test_get_connection_works(self, in_memory_db : DatabaseConnection):

        conn = in_memory_db.get_connection()

        assert isinstance(conn, sqlite3.Connection)

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result == (1,)
        cursor.close()
    

    def test_get_connection_resuses_same_connection(self, in_memory_db: DatabaseConnection):

        conn1 = in_memory_db.get_connection()
        conn2 = in_memory_db.get_connection()

        assert conn1 is conn2   


    def test_get_connection_different_threads(self, in_memory_db : DatabaseConnection):

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(in_memory_db.get_connection)
            future2 = executor.submit(in_memory_db.get_connection)

            result1 = future1.result()
            result2 = future2.result()

            assert result1 is not result2

    def test_execute_with_transaction_success(self, in_memory_db : DatabaseConnection):
        in_memory_db.execute_with_transaction("CREATE TABLE test_table (id INTEGER, name TEXT)")


        conn = in_memory_db.get_connection()

        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ('test_table',))
        result = cursor.fetchone()

        assert result is not None


    def test_execute_with_transaction_rollback_on_error(self, in_memory_db : DatabaseConnection):


        in_memory_db.execute_with_transaction("CREATE TABLE test (id INTEGER)")

        with pytest.raises(Exception):
            in_memory_db.execute_with_transaction("INVALID SQL GARBAGE")

        # Step 3: Verify the table still exists (transaction didn't mess up the connection)
        conn = in_memory_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
        result = cursor.fetchone()
        cursor.close()

        assert result is not None  # Table should still exist

    def test_execute_with_transaction_with_parameters(self, in_memory_db : DatabaseConnection):

        in_memory_db.execute_with_transaction("CREATE TABLE test (id INTEGER, number INTEGER)")
        in_memory_db.execute_with_transaction("INSERT INTO test (number) VALUES (?)",(1,))

        conn = in_memory_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT number FROM test")
        result = cursor.fetchone()

        assert result == (1,)


    
    def test_close_all_cleans_up_connection(self, in_memory_db : DatabaseConnection):

        assert isinstance(in_memory_db.local.connection, sqlite3.Connection)
        in_memory_db.close_connection()
        assert in_memory_db.local.connection is None
