# src/database/scrape_operations.py
"""
Database operations for raw scrape data.
Handles storing and retrieving raw HTML from scraping sessions.
"""
from __future__ import annotations
from .connection import DatabaseConnection
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
            raw_html = ""  # Avoid storing duplicate raw HTML
            is_duplicate = True
        else: 
            is_duplicate = False

        html_size = len(raw_html.encode('utf-8')) if raw_html else 0

        return self._insert_scrape_record(
            source_site, source_url, page_type, scrape_session_id,
            raw_html, html_size, response_status, content_hash, is_duplicate
        )

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
            FROM iran_jobs.raw_scrapes 
            WHERE content_hash = %s AND is_duplicate = FALSE
        """
        
        return self.db_connection.fetchone(query, (content_hash,))

    def _insert_scrape_record(
        self, 
        source_site: str, 
        source_url: str, 
        page_type: str, 
        scrape_session_id: str,
        raw_html: str, 
        html_size: int, 
        response_status: int, 
        content_hash: str, 
        is_duplicate: bool
    ) -> int:
        """
        Insert a new scrape record into the database.
        
        Returns:
            int: ID of inserted record
        """
        query = """
            INSERT INTO iran_jobs.raw_scrapes (
                source_site, source_url, page_type, scrape_session_id, 
                raw_html, html_size, response_status, content_hash, is_duplicate
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        return self.db_connection.execute_insert_with_id(
            query,
            (source_site, source_url, page_type, scrape_session_id, 
             raw_html, html_size, response_status, content_hash, is_duplicate)
        )