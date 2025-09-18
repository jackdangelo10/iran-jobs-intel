# tests/conftest.py
import pytest
from src.database.connection import DatabaseConnection
from src.database import IranJobsDB

@pytest.fixture
def in_memory_conn():
    db = DatabaseConnection(':memory:')
    yield db
    db.close_connection()

@pytest.fixture
def in_memory_db():
    db = IranJobsDB(':memory:')
    yield db
    db.close()