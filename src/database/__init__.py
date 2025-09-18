# database/__init__.py
from __future__ import annotations
from .connection import DatabaseConnection
from .company_operations import CompanyOperations
from .job_operations import JobOperations
from .scrape_operations import ScrapeOperations
from .schema import TABLE_ORDER, SCHEMA_SQL

class IranJobsDB:

    def __init__(self, db_path : str = "data/databases/iran_jobs.db"):
        self.db_path = db_path
        self.db_connection = DatabaseConnection(db_path)

        self.setup_database() # Create tables if they don't exist

        self.companies = CompanyOperations(self.db_connection)
        self.job = JobOperations(self.db_connection)
        self.scrapes = ScrapeOperations(self.db_connection)

        

    
    def setup_database(self):
        try:
            for key in TABLE_ORDER:
                self.db_connection.execute_with_transaction(SCHEMA_SQL[key])
        except Exception as e:
            print("Database tables initialization failed")
            raise



