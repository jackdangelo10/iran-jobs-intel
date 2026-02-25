# src/database/scrape_operations.py
"""
Database operations for raw scrape data.
Handles storing and retrieving raw HTML from scraping sessions.
"""
from __future__ import annotations
from .connection import DatabaseConnection
from .models import RawScrape
from ..utils.sha256_hash import sha256_hash


class ScrapeOperations:
    """Operations for managing raw scrape data."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    def save_raw_scrape(
        self, 
        source_site: str, 
        source_url: str, 
        page_type: str, 
        scrape_session_id: str,
        raw_html: str, 
        response_status: int
    ) -> int:
        """
        Save raw HTML scrape data to the database.
        
        Args:
            source_site: Site identifier (irantalent, jobvision, jobinja)
            source_url: URL that was scraped
            page_type: Type of page (job_list, job_detail, company_profile)
            scrape_session_id: UUID for this scraping session
            raw_html: Raw HTML content
            response_status: HTTP response status code
            
        Returns:
            int: ID of the inserted scrape record
        """
        content_hash = sha256_hash(raw_html)

        # Check for duplicate
        existing_scrape = self._get_by_content_hash(content_hash)
        if existing_scrape:
            raw_html_to_store = ""  # Avoid storing duplicate raw HTML
            is_duplicate = True
        else: 
            raw_html_to_store = raw_html
            is_duplicate = False

        html_size = len(raw_html.encode('utf-8')) if raw_html else 0

        # Create and validate model
        scrape = RawScrape(
            source_site=source_site,
            source_url=source_url,
            page_type=page_type,
            scrape_session_id=scrape_session_id,
            raw_html=raw_html_to_store,
            html_size=html_size,
            response_status=response_status,
            content_hash=content_hash,
            is_duplicate=is_duplicate
        )

        return self._insert_scrape_record(scrape)

    def _get_by_content_hash(self, content_hash: str) -> dict | None:
        """
        Retrieve a scrape record by its content hash.
        
        Args:
            content_hash: SHA-256 hash of content
            
        Returns:
            Dict with scrape record or None if not found
        """
        query = """
            SELECT id, raw_html 
            FROM raw_scrapes 
            WHERE content_hash = %s AND is_duplicate = FALSE
        """
        
        return self.db_connection.fetchone(query, (content_hash,))

    def _insert_scrape_record(self, scrape: RawScrape) -> int:
        """
        Insert a new scrape record into the database.
        
        Args:
            scrape: RawScrape model with data
            
        Returns:
            int: ID of inserted record
        """
        query = """
            INSERT INTO raw_scrapes (
                source_site, source_url, page_type, scrape_session_id, 
                raw_html, html_size, response_status, content_hash, is_duplicate
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        return self.db_connection.execute_insert_with_id(
            query,
            (scrape.source_site, scrape.source_url, scrape.page_type, 
             scrape.scrape_session_id, scrape.raw_html, scrape.html_size, 
             scrape.response_status, scrape.content_hash, scrape.is_duplicate)
        )

    def get_last_success_page(self, source_site: str) -> int:
        """
        Get the last successful discovery page for a source site.
        """
        query = """
            SELECT last_success_page
            FROM scrape_progress
            WHERE source_site = %s
        """
        result = self.db_connection.fetchone(query, (source_site,))
        if result and "last_success_page" in result:
            return int(result["last_success_page"])
        return 0

    def update_last_success_page(
        self,
        source_site: str,
        last_success_page: int,
        session_id: str | None = None
    ) -> None:
        """
        Upsert last successful discovery page for a source site.
        Logs a warning on failure rather than raising, so a DB permission issue
        cannot cause the scraper to loop indefinitely on the same page.
        """
        import logging
        query = """
            INSERT INTO scrape_progress (
                source_site, last_success_page, last_success_at, last_session_id
            )
            VALUES (%s, %s, NOW(), %s)
            ON CONFLICT (source_site) DO UPDATE SET
                last_success_page = EXCLUDED.last_success_page,
                last_success_at = EXCLUDED.last_success_at,
                last_session_id = EXCLUDED.last_session_id
        """
        try:
            self.db_connection.execute_with_transaction(
                query, (source_site, last_success_page, session_id)
            )
        except Exception as e:
            logging.getLogger(__name__).warning(
                "Failed to update scrape_progress for %s page %d: %s",
                source_site, last_success_page, e
            )
