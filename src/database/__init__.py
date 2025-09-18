# database/__init__.py
from __future__ import annotations
from .connection import DatabaseConnection

class IranJobsDB:

    def __init__(self, db_path : str = "data/databases/iran_jobs.db"):
        self.db_path = db_path
        self.db_connection = DatabaseConnection(db_path)


