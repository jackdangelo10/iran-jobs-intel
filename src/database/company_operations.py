# src/database/company_operations.py
"""
Database operations for company tracking and discovery.
Handles company URL discovery and profile scraping status.
"""
from __future__ import annotations
from .connection import DatabaseConnection


class CompanyOperations:
    """Operations for managing company data and tracking."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    def track_company_discovery(
        self, 
        company_url: str, 
        source_site: str, 
        session_id: str
    ) -> None:
        """
        Track discovered company URL for later scraping.
        
        Creates a new tracking record if the company is new, or updates
        the last_seen fields if it already exists.
        
        Args:
            company_url: URL of the company profile page
            source_site: Site where company was found (irantalent, jobvision, jobinja)
            session_id: Current scraping session UUID
        """
        # Check if company already exists
        existing = self._get_company_tracking(company_url)
        
        if not existing:
            # Insert new company tracking record
            query = """
                INSERT INTO iran_jobs.company_tracking (
                    company_url, source_site, first_seen_session, 
                    last_seen_session, first_seen_date, last_seen_date
                )
                VALUES (%s, %s, %s, %s, CURRENT_DATE, CURRENT_DATE)
            """
            self.db_connection.execute_with_transaction(
                query, 
                (company_url, source_site, session_id, session_id)
            )
        else:
            # Update last seen information
            query = """
                UPDATE iran_jobs.company_tracking 
                SET last_seen_session = %s, last_seen_date = CURRENT_DATE
                WHERE company_url = %s
            """
            self.db_connection.execute_with_transaction(
                query, 
                (session_id, company_url)
            )

    def _get_company_tracking(self, company_url: str) -> dict | None:
        """
        Check if company URL is already being tracked.
        
        Args:
            company_url: URL to check
            
        Returns:
            Dict with tracking record or None if not found
        """
        query = """
            SELECT id, company_url, source_site, first_seen_date, last_seen_date
            FROM iran_jobs.company_tracking
            WHERE company_url = %s
        """
        
        return self.db_connection.fetchone(query, (company_url,))