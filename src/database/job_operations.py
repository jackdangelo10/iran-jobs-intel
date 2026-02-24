# src/database/job_operations.py
"""
Database operations for job postings, discoveries, and tracking.
Handles job URL discovery, lifecycle tracking, and saving job details.
"""
from __future__ import annotations
from typing import Any
from datetime import date
from .connection import DatabaseConnection
from .models import JobPosting, JobDiscovery, JobTracking


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
        # Create and validate model
        discovery = JobDiscovery(
            scrape_session_id=scrape_session_id,
            job_url=job_url,
            source_site=source_site,
            company_url=company_url,
            found_on_page=found_on_page
        )
        
        query = """
            INSERT INTO iran_jobs.job_discoveries (
                scrape_session_id, job_url, company_url, source_site, found_on_page
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """

        return self.db_connection.execute_insert_with_id(
            query,
            (discovery.scrape_session_id, discovery.job_url, discovery.company_url, 
             discovery.source_site, discovery.found_on_page)
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
            # Create and validate model
            today = date.today()
            tracking = JobTracking(
                job_url=job_url,
                source_site=source_site,
                first_seen_session=session_id,
                last_seen_session=session_id,
                first_seen_date=today,
                last_seen_date=today
            )
            
            # Insert new tracking record
            query = """
                INSERT INTO iran_jobs.job_tracking (
                    job_url, source_site, first_seen_session, 
                    last_seen_session, first_seen_date, last_seen_date
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.db_connection.execute_with_transaction(
                query, 
                (tracking.job_url, tracking.source_site, 
                 tracking.first_seen_session, tracking.last_seen_session,
                 tracking.first_seen_date, tracking.last_seen_date)
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

    def save_job_posting(self, job_data: dict[str, Any] | JobPosting) -> int:
        """
        Save a scraped job posting to the database.

        Uses ON CONFLICT (source_site, external_id) to handle re-scrapes safely:
        - Updates last_seen_date and restores is_active = TRUE
        - Fills in missing description/scrape_id from the new scrape

        Args:
            job_data: Dict or JobPosting model with job data

        Returns:
            int: ID of the inserted (or existing) job posting
        """
        # Convert dict to model if needed (validates data)
        if isinstance(job_data, dict):
            today = date.today()
            if 'first_seen_date' not in job_data:
                job_data['first_seen_date'] = today
            if 'last_seen_date' not in job_data:
                job_data['last_seen_date'] = today
            job = JobPosting(**job_data)
        else:
            job = job_data

        # Convert to database format (handles JSON serialization)
        db_data = job.to_db_dict()

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
            ON CONFLICT (source_site, external_id) DO UPDATE SET
                last_seen_date      = EXCLUDED.last_seen_date,
                is_active           = TRUE,
                raw_scrape_id       = COALESCE(EXCLUDED.raw_scrape_id,
                                               iran_jobs.job_postings.raw_scrape_id),
                description_persian = COALESCE(EXCLUDED.description_persian,
                                               iran_jobs.job_postings.description_persian),
                company_name_raw    = COALESCE(EXCLUDED.company_name_raw,
                                               iran_jobs.job_postings.company_name_raw),
                location_raw        = COALESCE(EXCLUDED.location_raw,
                                               iran_jobs.job_postings.location_raw)
            RETURNING id
        """

        return self.db_connection.execute_insert_with_id(query, (
            db_data.get('raw_scrape_id'),
            db_data.get('external_id'),
            db_data.get('source_site'),
            db_data.get('source_url'),
            db_data.get('title_persian'),
            db_data.get('title_english'),
            db_data.get('description_persian'),
            db_data.get('description_english'),
            db_data.get('company_name_raw'),
            db_data.get('company_url'),
            db_data.get('location_raw'),
            db_data.get('employment_type'),
            db_data.get('experience_level'),
            db_data.get('gender_requirement'),
            db_data.get('education_level'),
            db_data.get('salary_min_original'),
            db_data.get('salary_max_original'),
            db_data.get('salary_currency_original'),
            db_data.get('skills_required_json'),
            db_data.get('skills_preferred_json'),
            db_data.get('technologies_mentioned_json'),
            db_data.get('posted_date'),
            db_data.get('first_seen_date'),
            db_data.get('last_seen_date'),
            db_data.get('processing_status', 'pending')
        ))

    def deactivate_stale_jobs(self, days_threshold: int = 14) -> int:
        """
        Mark job postings as inactive if they haven't been seen in recent scrapes.

        A job is considered gone from the site if its last_seen_date is older
        than `days_threshold` days and it is currently marked active.

        Args:
            days_threshold: Number of days without a sighting before deactivation.

        Returns:
            Number of jobs deactivated.
        """
        result = self.db_connection.execute_write_returning(
            """
            WITH updated AS (
                UPDATE iran_jobs.job_postings
                SET is_active = FALSE,
                    deactivated_date = CURRENT_DATE
                WHERE last_seen_date < CURRENT_DATE - %s
                  AND is_active = TRUE
                RETURNING id
            )
            SELECT COUNT(*)::int AS count FROM updated
            """,
            (days_threshold,),
        )
        return result[0]["count"] if result else 0

    def get_active_company_job_counts(self) -> list[dict[str, Any]]:
        """
        Return per-company counts of active job postings plus 30-day velocity.

        Returns:
            List of dicts: company_id, active_count, count_30d
        """
        return self.db_connection.fetchall(
            """
            SELECT
                company_id,
                COUNT(*)::int                                                     AS active_count,
                COUNT(*) FILTER (WHERE first_seen_date >= CURRENT_DATE - 30)::int AS count_30d
            FROM iran_jobs.job_postings
            WHERE company_id IS NOT NULL
              AND is_active = TRUE
            GROUP BY company_id
            """
        )

    def get_unprocessed_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get job postings that need processing (translation, extraction, etc.).
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of dicts with job posting data
        """
        query = """
            SELECT id, title_persian, description_persian, company_name_raw, 
                   location_raw, source_site, external_id
            FROM iran_jobs.job_postings
            WHERE processing_status = 'pending'
            ORDER BY first_seen_date DESC
            LIMIT %s
        """
        
        return self.db_connection.fetchall(query, (limit,))