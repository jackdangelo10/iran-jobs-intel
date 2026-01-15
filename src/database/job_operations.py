# src/database/job_operations.py
"""
Database operations for job postings, discoveries, and tracking.
Handles job URL discovery, lifecycle tracking, and saving job details.
"""
from __future__ import annotations
from typing import Any
from datetime import datetime, timezone
import json
from .connection import DatabaseConnection


class JobOperations:
    """Operations for managing job posting data and tracking."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    def record_job_discovery(
        self, 
        scrape_session_id: str, 
        job_url: str, 
        source_site: str, 
        company_url: str | None = None, 
        found_on_page: str | None = None
    ) -> int:
        """
        Record a discovered job URL during scraping.
        
        Args:
            scrape_session_id: UUID for this scraping session
            job_url: URL of the job posting
            source_site: Site where job was found
            company_url: URL of company profile (if available)
            found_on_page: URL of the listing page where job was found
            
        Returns:
            int: ID of the job discovery record
        """
        query = """
            INSERT INTO iran_jobs.job_discoveries (
                scrape_session_id, job_url, company_url, source_site, found_on_page
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """

        return self.db_connection.execute_insert_with_id(
            query,
            (scrape_session_id, job_url, company_url, source_site, found_on_page)
        )

    def update_job_tracking(
        self, 
        job_url: str, 
        source_site: str, 
        session_id: str
    ) -> None:
        """
        Update job tracking lifecycle information.
        
        Creates a new tracking record if job is new, or updates the
        last_seen fields if it already exists.
        
        Args:
            job_url: URL of the job posting
            source_site: Site identifier
            session_id: Current scraping session UUID
        """
        # Check if job already exists
        existing = self._get_job_tracking(job_url)
        
        if existing:
            # Update last_seen fields only
            query = """
                UPDATE iran_jobs.job_tracking 
                SET last_seen_session = %s, last_seen_date = CURRENT_DATE
                WHERE job_url = %s
            """
            self.db_connection.execute_with_transaction(query, (session_id, job_url))
        else:
            # Insert new tracking record
            query = """
                INSERT INTO iran_jobs.job_tracking (
                    job_url, source_site, first_seen_session, 
                    last_seen_session, first_seen_date, last_seen_date
                )
                VALUES (%s, %s, %s, %s, CURRENT_DATE, CURRENT_DATE)
            """
            self.db_connection.execute_with_transaction(
                query, 
                (job_url, source_site, session_id, session_id)
            )

    def _get_job_tracking(self, job_url: str) -> bool:
        """
        Check if job URL is already being tracked.
        
        Args:
            job_url: URL to check
            
        Returns:
            bool: True if job exists and is active
        """
        query = """
            SELECT 1
            FROM iran_jobs.job_tracking
            WHERE job_url = %s AND is_active = TRUE
        """
        
        result = self.db_connection.fetchone(query, (job_url,))
        return result is not None

    def get_jobs_needing_scraping(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get list of job URLs that need detailed scraping.
        
        Returns jobs that haven't been scraped yet, ordered by
        first_seen_date (oldest first).
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of dicts with job tracking information
        """
        query = """
            SELECT job_url, source_site, first_seen_date, detail_scrape_count
            FROM iran_jobs.job_tracking 
            WHERE detail_scraped = FALSE AND is_active = TRUE
            ORDER BY first_seen_date ASC
            LIMIT %s
        """
        
        return self.db_connection.fetchall(query, (limit,))

    def mark_job_scraped(self, job_url: str, success: bool = True) -> None:
        """
        Mark a job as scraped (or increment failure count).
        
        Args:
            job_url: URL that was scraped
            success: Whether the scraping was successful
        """
        if success:
            query = """
                UPDATE iran_jobs.job_tracking 
                SET detail_scraped = TRUE, 
                    last_detail_scrape_date = CURRENT_DATE,
                    detail_scrape_count = detail_scrape_count + 1
                WHERE job_url = %s
            """
        else:
            # Failed scrape - increment count but don't mark as completed
            query = """
                UPDATE iran_jobs.job_tracking 
                SET detail_scrape_count = detail_scrape_count + 1,
                    last_detail_scrape_date = CURRENT_DATE
                WHERE job_url = %s
            """
        
        self.db_connection.execute_with_transaction(query, (job_url,))

    def save_job_posting(self, job_data: dict[str, Any]) -> int:
        """
        Save a scraped job posting to the database.
        
        Args:
            job_data: Dict containing all job posting fields
            
        Returns:
            int: ID of the inserted job posting
        """
        # Handle JSON fields
        skills_required = json.dumps(job_data.get('skills_required', [])) if job_data.get('skills_required') else None
        skills_preferred = json.dumps(job_data.get('skills_preferred', [])) if job_data.get('skills_preferred') else None
        technologies_mentioned = json.dumps(job_data.get('technologies_mentioned', [])) if job_data.get('technologies_mentioned') else None

        # Handle date - use current date for first/last seen
        today = datetime.now(timezone.utc).date().isoformat()
        
        query = """
            INSERT INTO iran_jobs.job_postings (
                raw_scrape_id, external_id, source_site, source_url,
                title_persian, title_english, description_persian, description_english,
                company_name_raw, company_url, location_raw, employment_type, experience_level,
                gender_requirement, education_level,
                salary_min_original, salary_max_original, salary_currency_original,
                skills_required_json, skills_preferred_json, technologies_mentioned_json,
                posted_date, first_seen_date, last_seen_date, processing_status
            ) 
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
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
            job_data.get('company_url'),
            job_data.get('location_raw'),
            job_data.get('employment_type'),
            job_data.get('experience_level'),
            job_data.get('gender_requirement'),
            job_data.get('education_level'),
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