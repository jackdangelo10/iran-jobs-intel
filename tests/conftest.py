# tests/conftest.py
import pytest
from src.database.connection import DatabaseConnection

@pytest.fixture
def in_memory_db():
    db = DatabaseConnection(':memory:')
    yield db
    db.close_connection()