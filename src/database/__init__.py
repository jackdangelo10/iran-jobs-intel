# src/database/__init__.py
"""
Database module for Iran Jobs Intelligence Platform.
Handles PostgreSQL connection and table setup.
"""
from __future__ import annotations
from .connection import DatabaseConnection
from .company_operations import CompanyOperations
from .job_operations import JobOperations
from .scrape_operations import ScrapeOperations
from .schema import TABLE_ORDER, SCHEMA_SQL


class IranJobsDB:
    """
    Main database interface for Iran Jobs Intelligence Platform.
    
    Manages PostgreSQL connection, schema setup, and provides access
    to operation classes for different entity types.
    """

    def __init__(self, conninfo: str | None = None):
        """
        Initialize database connection and setup schema.
        
        Args:
            conninfo: PostgreSQL connection string. If None, uses settings.database_url
        """
        self.db_connection = DatabaseConnection(conninfo)
        
        # Setup database schema (creates tables if they don't exist)
        self.setup_database()
        
        # Initialize operation classes
        self.companies = CompanyOperations(self.db_connection)
        self.jobs = JobOperations(self.db_connection)
        self.scrapes = ScrapeOperations(self.db_connection)

    def setup_database(self):
        """
        Setup database schema - creates tables and indexes if they don't exist.
        
        This method is idempotent - safe to run multiple times.
        Uses IF NOT EXISTS clauses so existing tables are not affected.
        """
        print("🔧 Setting up database schema...")
        
        conn = self.db_connection.get_connection()
        
        try:
            # Execute each SQL statement in order
            for key in TABLE_ORDER:
                sql = SCHEMA_SQL[key]
                
                # Check if this is an index creation statement (multiple statements)
                if 'indexes' in key:
                    # Index creation - execute as single string (can contain multiple CREATE INDEX)
                    with conn.cursor() as cursor:
                        cursor.execute(self.db_connection._to_literal(sql))
                else:
                    # Table creation - single statement
                    with conn.cursor() as cursor:
                        cursor.execute(self.db_connection._to_literal(sql))
            
            conn.commit()
            print("✅ Database schema setup complete")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Database schema setup failed: {e}")
            raise
        finally:
            self.db_connection.return_connection(conn)

    def close(self):
        """Close database connection pool."""
        self.db_connection.close_connection()