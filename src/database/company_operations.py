# src/database/company_operations.py
"""
Database operations for company tracking and discovery.
Handles company URL discovery and profile scraping status.
"""
from __future__ import annotations
from datetime import date
from .connection import DatabaseConnection
from .models import CompanyTracking


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
            # Create and validate model
            today = date.today()
            tracking = CompanyTracking(
                company_url=company_url,
                source_site=source_site,
                first_seen_session=session_id,
                last_seen_session=session_id,
                first_seen_date=today,
                last_seen_date=today
            )
            
            # Insert new company tracking record
            query = """
                INSERT INTO iran_jobs.company_tracking (
                    company_url, source_site, first_seen_session, 
                    last_seen_session, first_seen_date, last_seen_date
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.db_connection.execute_with_transaction(
                query, 
                (tracking.company_url, tracking.source_site, 
                 tracking.first_seen_session, tracking.last_seen_session,
                 tracking.first_seen_date, tracking.last_seen_date)
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

    def get_companies_needing_scraping(self, limit: int = 50) -> list[dict]:
        """
        Get list of company URLs that need profile scraping.
        
        Args:
            limit: Maximum number of companies to return
            
        Returns:
            List of dicts with company tracking information
        """
        query = """
            SELECT company_url, source_site, first_seen_date, profile_scrape_count
            FROM iran_jobs.company_tracking
            WHERE profile_scraped = FALSE
            ORDER BY first_seen_date ASC
            LIMIT %s
        """
        
        return self.db_connection.fetchall(query, (limit,))

    def mark_company_scraped(self, company_url: str, success: bool = True) -> None:
        """
        Mark a company profile as scraped (or increment failure count).
        
        Args:
            company_url: URL that was scraped
            success: Whether the scraping was successful
        """
        if success:
            query = """
                UPDATE iran_jobs.company_tracking 
                SET profile_scraped = TRUE, 
                    last_profile_scrape_date = CURRENT_DATE,
                    profile_scrape_count = profile_scrape_count + 1
                WHERE company_url = %s
            """
        else:
            # Failed scrape - increment count but don't mark as completed
            query = """
                UPDATE iran_jobs.company_tracking 
                SET profile_scrape_count = profile_scrape_count + 1,
                    last_profile_scrape_date = CURRENT_DATE
                WHERE company_url = %s
            """
        
        self.db_connection.execute_with_transaction(query, (company_url,))