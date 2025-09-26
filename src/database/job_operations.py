# database/job_operations.py
from __future__ import annotations
from typing import List, Dict, Optional, Any
import sqlite3
from datetime import date, datetime, timezone
import json

class JobOperations:

    def __init__(self, db_connection):
        self.db_connection = db_connection

    def record_job_discovery(self, scrape_session_id: str, job_url: str, 
                            source_site: str, company_url: Optional[str] = None, 
                            found_on_page: Optional[str] = None) -> int:
        query = """
            INSERT INTO job_discoveries (scrape_session_id, job_url, company_url, source_site, found_on_page)
            VALUES (?, ?, ?, ?, ?)
        """

        return self.db_connection.execute_insert_with_id(query,
            (scrape_session_id, job_url, company_url, source_site, found_on_page)
        )
    

    def _get_job_tracking(self, job_url: str):
        query = """
            SELECT 1
            FROM job_tracking
            WHERE job_url = ? AND is_active = TRUE
        """
        conn = self.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (job_url,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    
    def update_job_tracking(self, job_url: str, source_site: str, session_id: str) -> None:
        
        # Try and find existing job url:
        existing = self._get_job_tracking(job_url)
        
        if existing:
            # Update last_seen fields only
            query = """
                UPDATE job_tracking 
                SET last_seen_session = ?, last_seen_date = DATE('now')
                WHERE job_url = ?
            """
            self.db_connection.execute_with_transaction(query, (session_id, job_url))
        else:
            # Insert new record
            query = """
                INSERT INTO job_tracking (job_url, source_site, first_seen_session, 
                                        last_seen_session, first_seen_date, last_seen_date)
                VALUES (?, ?, ?, ?, DATE('now'), DATE('now'))
            """
            self.db_connection.execute_with_transaction(query, (job_url, source_site, session_id, session_id))

    
    def get_jobs_needing_scraping(self, limit: int = 100) -> List[Dict[str, Any]]:
        query = """
            SELECT job_url, source_site, first_seen_date, detail_scrape_count
            FROM job_tracking 
            WHERE detail_scraped = FALSE AND is_active = TRUE
            ORDER BY first_seen_date ASC
            LIMIT ?
        """
        conn = self.db_connection.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        return results

    def mark_job_scraped(self, job_url: str, success: bool = True) -> None:
        if success:
            query = """
                UPDATE job_tracking 
                SET detail_scraped = TRUE, 
                    last_detail_scrape_date = DATE('now'),
                    detail_scrape_count = detail_scrape_count + 1
                WHERE job_url = ?
            """
        else:
            # Failed scrape - increment count but don't mark as completed
            query = """
                UPDATE job_tracking 
                SET detail_scrape_count = detail_scrape_count + 1,
                    last_detail_scrape_date = DATE('now')
                WHERE job_url = ?
            """
        
        self.db_connection.execute_with_transaction(query, (job_url,))

    
    def save_job_posting(self, job_data: Dict[str, Any]) -> int:

        # Handle json fields
        skills_required = json.dumps(job_data.get('skills_required', [])) if job_data.get('skills_required') else None
        skills_preferred = json.dumps(job_data.get('skills_preferred', [])) if job_data.get('skills_preferred') else None
        technologies_mentioned = json.dumps(job_data.get('technologies_mentioned', [])) if job_data.get('technologies_mentioned') else None

        # Handle date
        today = datetime.now(timezone.utc).date().isoformat()
        query = """
            INSERT INTO job_postings (
                raw_scrape_id, external_id, source_site, source_url,
                title_persian, title_english, description_persian, description_english,
                company_name_raw, location_raw, employment_type, experience_level,
                salary_min_original, salary_max_original, salary_currency_original,
                skills_required_json, skills_preferred_json, technologies_mentioned_json,
                posted_date, first_seen_date, last_seen_date, processing_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        return self.db_connection.execute_insert_with_id(query, (
            job_data.get('raw_scrape_id'),
            job_data.get('external_id'),
            job_data.get('source_site'),
            job_data.get('source_url'),
            job_data.get('title_persian'),
            job_data.get('title_english'),
            job_data.get('description_persian'),
            job_data.get('description_english'),
            job_data.get('company_name_raw'),
            job_data.get('location_raw'),
            job_data.get('employment_type'),
            job_data.get('experience_level'),
            job_data.get('salary_min_original'),
            job_data.get('salary_max_original'),
            job_data.get('salary_currency_original'),
            skills_required,
            skills_preferred,
            technologies_mentioned,
            job_data.get('posted_date'),
            job_data.get('first_seen_date', today),
            job_data.get('last_seen_date', today),
            job_data.get('processing_status', 'pending')
        ))

