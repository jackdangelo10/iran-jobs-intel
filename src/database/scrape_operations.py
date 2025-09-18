# database/scrape_operations.py
from __future__ import annotations
from typing import Optional
from .connection import DatabaseConnection
from ..utils.sha256_hash import sha256_hash

class ScrapeOperations:

    def __init__(self, db_connection):
        self.db_connection : DatabaseConnection = db_connection


    def save_raw_scrape(self, source_site : str, source_url : str, page_type : str, scrape_session_id : str,
                        raw_html : str, response_status : int) -> int:
        """Saves raw HTML scrape data to the database."""

        content_hash = sha256_hash(raw_html)

        existing_scrape = self._get_by_content_hash(content_hash)
        if existing_scrape:
            raw_html = ""  # Avoid storing duplicate raw HTML
            is_duplicate = True
        else: 
            is_duplicate = False

        html_size = len(raw_html.encode('utf-8')) if raw_html else 0

        return self._insert_scrape_record(source_site, source_url, page_type, scrape_session_id,
                                          raw_html, html_size, response_status, content_hash, is_duplicate)

    def _get_by_content_hash(self, content_hash : str) -> Optional[dict]:
        """Retrieves a scrape record by its content hash."""
        query = "SELECT id, raw_html FROM raw_scrapes WHERE content_hash = ? AND is_duplicate = FALSE"

        conn = self.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (content_hash,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return {'id': result[0], 'raw_html': result[1]}
        return None
    

    def _insert_scrape_record(self, source_site : str, source_url : str, page_type : str, scrape_session_id : str,
                              raw_html : str, html_size : int, response_status : int, content_hash : str, is_duplicate : bool) -> int:
        """Inserts a new scrape record into the database."""
        query = """
            INSERT INTO raw_scrapes (source_site, source_url, page_type, scrape_session_id, 
                                     raw_html, html_size, response_status, content_hash, is_duplicate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        return self.db_connection.execute_insert_with_id(query, 
            (source_site, source_url, page_type, scrape_session_id, raw_html, html_size, response_status, content_hash, is_duplicate)
        )


    