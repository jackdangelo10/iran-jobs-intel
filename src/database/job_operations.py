# database/job_operations.py
from __future__ import annotations

class JobOperations:

    def __init__(self, db_connection):
        self.db_connection = db_connection