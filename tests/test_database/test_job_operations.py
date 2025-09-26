# tests/test_database/test_job_operations.py
import pytest
import json
from datetime import date
from src.database import IranJobsDB
from datetime import date, datetime, timezone

class TestJobOperations:
    
    def test_record_job_discovery(self, in_memory_db):
        """Test basic job discovery recording"""
        discovery_id = in_memory_db.jobs.record_job_discovery(
            scrape_session_id="test-session-123",
            job_url="https://irantalent.com/jobs/12345",
            source_site="irantalent",
            company_url="https://irantalent.com/company/google",
            found_on_page="https://irantalent.com/jobs?page=1"
        )
        
        assert isinstance(discovery_id, int)
        assert discovery_id > 0
        
        # Verify it was inserted correctly
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_discoveries WHERE id = ?", (discovery_id,))
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None
        assert result[1] == "test-session-123"  # scrape_session_id
        assert result[2] == "https://irantalent.com/jobs/12345"  # job_url
        assert result[3] == "https://irantalent.com/company/google"  # company_url
        assert result[4] == "irantalent"  # source_site
        assert result[5] == "https://irantalent.com/jobs?page=1"  # found_on_page
    
    def test_record_job_discovery_minimal_data(self, in_memory_db):
        """Test job discovery with only required fields"""
        discovery_id = in_memory_db.jobs.record_job_discovery(
            scrape_session_id="test-session-456",
            job_url="https://irantalent.com/jobs/67890",
            source_site="irantalent"
        )
        
        assert isinstance(discovery_id, int)
        assert discovery_id > 0
        
        # Verify optional fields are None
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT company_url, found_on_page FROM job_discoveries WHERE id = ?", (discovery_id,))
        result = cursor.fetchone()
        cursor.close()
        
        assert result[0] is None  # company_url
        assert result[1] is None  # found_on_page
    
    def test_update_job_tracking_new_job(self, in_memory_db):
        """Test tracking a job for the first time"""
        job_url = "https://irantalent.com/jobs/new-job-123"
        
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "session-001")
        
        # Verify job was inserted
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_url, source_site, first_seen_session, last_seen_session, 
                first_seen_date, last_seen_date, is_active, detail_scraped
            FROM job_tracking WHERE job_url = ?
        """, (job_url,))
        result = cursor.fetchone()
        cursor.close()
        
        # Get UTC date like SQLite does
        utc_date = datetime.now(timezone.utc).date().isoformat()
        
        assert result is not None
        assert result[0] == job_url
        assert result[1] == "irantalent"
        assert result[2] == "session-001"  # first_seen_session
        assert result[3] == "session-001"  # last_seen_session
        assert result[4] == utc_date  # first_seen_date
        assert result[5] == utc_date  # last_seen_date
        assert result[6] == 1  # is_active (True)
        assert result[7] == 0  # detail_scraped (False)
    
    def test_update_job_tracking_existing_job(self, in_memory_db):
        """Test updating an existing job's last seen info"""
        job_url = "https://irantalent.com/jobs/existing-job-456"
        
        # First insert
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "session-001")
        
        # Update with new session
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "session-002")
        
        # Verify update
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_seen_session, last_seen_session 
            FROM job_tracking WHERE job_url = ?
        """, (job_url,))
        result = cursor.fetchone()
        cursor.close()
        
        assert result[0] == "session-001"  # first_seen_session unchanged
        assert result[1] == "session-002"  # last_seen_session updated
    
    def test_job_tracking_preserves_first_seen(self, in_memory_db):
        """Ensure first_seen fields don't change on updates"""
        job_url = "https://irantalent.com/jobs/preserve-test-789"
        
        # First tracking
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "first-session")
        
        # Get original first_seen values
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_seen_session, first_seen_date 
            FROM job_tracking WHERE job_url = ?
        """, (job_url,))
        original = cursor.fetchone()
        cursor.close()
        
        # Update multiple times
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "second-session")
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "third-session")
        
        # Verify first_seen fields unchanged
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_seen_session, first_seen_date, last_seen_session 
            FROM job_tracking WHERE job_url = ?
        """, (job_url,))
        updated = cursor.fetchone()
        cursor.close()
        
        assert updated[0] == original[0]  # first_seen_session unchanged
        assert updated[1] == original[1]  # first_seen_date unchanged
        assert updated[2] == "third-session"  # last_seen_session updated
    
    def test_get_jobs_needing_scraping(self, in_memory_db):
        """Test retrieving jobs that need detail scraping"""
        # Add some jobs to tracking
        job_urls = [
            "https://irantalent.com/jobs/need-scraping-1",
            "https://irantalent.com/jobs/need-scraping-2", 
            "https://irantalent.com/jobs/already-scraped-3"
        ]
        
        for url in job_urls:
            in_memory_db.jobs.update_job_tracking(url, "irantalent", "session-001")
        
        # Mark one as already scraped
        in_memory_db.jobs.mark_job_scraped(job_urls[2], success=True)
        
        # Get jobs needing scraping
        unscraped = in_memory_db.jobs.get_jobs_needing_scraping()
        
        assert len(unscraped) == 2
        unscraped_urls = [job['job_url'] for job in unscraped]
        assert job_urls[0] in unscraped_urls
        assert job_urls[1] in unscraped_urls
        assert job_urls[2] not in unscraped_urls  # Already scraped, excluded
        
        # Check return format
        assert isinstance(unscraped[0], dict)
        assert 'job_url' in unscraped[0]
        assert 'source_site' in unscraped[0]
        assert 'first_seen_date' in unscraped[0]
        assert 'detail_scrape_count' in unscraped[0]
    
    def test_get_jobs_needing_scraping_limit(self, in_memory_db):
        """Test limit parameter in get_jobs_needing_scraping"""
        # Add 5 jobs
        for i in range(5):
            job_url = f"https://irantalent.com/jobs/limit-test-{i}"
            in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "session-001")
        
        # Get with limit
        unscraped = in_memory_db.jobs.get_jobs_needing_scraping(limit=3)
        
        assert len(unscraped) == 3
    
    def test_mark_job_scraped_success(self, in_memory_db):
        """Test marking job as successfully scraped"""
        job_url = "https://irantalent.com/jobs/mark-scraped-success"
        
        # Add job to tracking
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "session-001")
        
        # Mark as scraped
        in_memory_db.jobs.mark_job_scraped(job_url, success=True)
        
        # Verify update
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT detail_scraped, detail_scrape_count, last_detail_scrape_date 
            FROM job_tracking WHERE job_url = ?
        """, (job_url,))
        result = cursor.fetchone()
        cursor.close()
        utc_date = datetime.now(timezone.utc).date().isoformat()
        assert result[0] == 1  # detail_scraped = True
        assert result[1] == 1  # detail_scrape_count incremented
        assert result[2] == utc_date  # last_detail_scrape_date updated

    def test_mark_job_scraped_failure(self, in_memory_db):
        """Test marking job scrape as failed"""
        job_url = "https://irantalent.com/jobs/mark-scraped-failure"
        
        # Add job to tracking
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", "session-001")
        
        # Mark scrape as failed
        in_memory_db.jobs.mark_job_scraped(job_url, success=False)
        
        # Verify update
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT detail_scraped, detail_scrape_count 
            FROM job_tracking WHERE job_url = ?
        """, (job_url,))
        result = cursor.fetchone()
        cursor.close()
        
        assert result[0] == 0  # detail_scraped still False
        assert result[1] == 1  # detail_scrape_count still incremented
    
    def test_save_job_posting(self, in_memory_db):
        """Test saving complete job posting data"""
        job_data = {
            'external_id': 'ext-123',
            'source_site': 'irantalent',
            'source_url': 'https://irantalent.com/jobs/test-job',
            'title_persian': 'مهندس نرم افزار',
            'title_english': 'Software Engineer',
            'description_persian': 'توضیحات شغل',
            'description_english': 'Job description',
            'company_name_raw': 'Google Iran',
            'location_raw': 'Tehran',
            'employment_type': 'full_time',
            'experience_level': 'mid',
            'salary_min_original': 50000000,
            'salary_max_original': 80000000,
            'salary_currency_original': 'IRR',
            'skills_required': ['Python', 'Django', 'React'],
            'skills_preferred': ['AWS', 'Docker'],
            'technologies_mentioned': ['PostgreSQL', 'Redis'],
            'posted_date': '2024-01-15',
            'processing_status': 'processed'
        }
        
        job_id = in_memory_db.jobs.save_job_posting(job_data)
        
        assert isinstance(job_id, int)
        assert job_id > 0
        
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT external_id, source_site, title_persian, title_english, 
                company_name_raw, location_raw, skills_required_json, skills_preferred_json
            FROM job_postings WHERE id = ?
        """, (job_id,))
        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == 'ext-123'  # external_id
        assert result[1] == 'irantalent'  # source_site
        assert result[2] == 'مهندس نرم افزار'  # title_persian
        assert result[3] == 'Software Engineer'  # title_english
        assert result[4] == 'Google Iran'  # company_name_raw
        assert result[5] == 'Tehran'  # location_raw

        # Check JSON fields were serialized correctly
        skills_required = json.loads(result[6])  # skills_required_json
        assert skills_required == ['Python', 'Django', 'React']

        skills_preferred = json.loads(result[7])  # skills_preferred_json
        assert skills_preferred == ['AWS', 'Docker']

    
    def test_save_job_posting_minimal_data(self, in_memory_db):
        """Test saving job posting with only required fields"""
        job_data = {
            'source_site': 'irantalent',
            'source_url': 'https://irantalent.com/jobs/minimal-test',
            'title_persian': 'عنوان شغل'
        }
        
        job_id = in_memory_db.jobs.save_job_posting(job_data)
        
        assert isinstance(job_id, int)
        assert job_id > 0
        
        # Verify defaults were applied
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT processing_status, first_seen_date FROM job_postings WHERE id = ?", (job_id,))
        result = cursor.fetchone()
        cursor.close()
        utc_date = datetime.now(timezone.utc).date().isoformat()
        assert result[0] == 'pending'  # default processing_status
        assert result[1] == utc_date  # default first_seen_date

    def test_complete_job_workflow(self, in_memory_db):
        """Test the complete job discovery and processing workflow"""
        session_id = "workflow-test-session"
        job_url = "https://irantalent.com/jobs/workflow-test"
        
        # Step 1: Discovery
        discovery_id = in_memory_db.jobs.record_job_discovery(
            scrape_session_id=session_id,
            job_url=job_url,
            source_site="irantalent",
            found_on_page="https://irantalent.com/jobs?page=1"
        )
        assert discovery_id > 0
        
        # Step 2: Job tracking
        in_memory_db.jobs.update_job_tracking(job_url, "irantalent", session_id)
        
        # Step 3: Check jobs needing scraping
        unscraped = in_memory_db.jobs.get_jobs_needing_scraping()
        assert len(unscraped) == 1
        assert unscraped[0]['job_url'] == job_url
        
        # Step 4: Save job posting data
        job_data = {
            'external_id': 'workflow-ext-123',
            'source_site': 'irantalent',
            'source_url': job_url,
            'title_persian': 'تست گردش کار',
            'title_english': 'Workflow Test',
            'company_name_raw': 'Test Company'
        }
        job_id = in_memory_db.jobs.save_job_posting(job_data)
        assert job_id > 0
        
        # Step 5: Mark job as scraped
        in_memory_db.jobs.mark_job_scraped(job_url, success=True)
        
        # Step 6: Verify job no longer appears in needing scraping
        unscraped_after = in_memory_db.jobs.get_jobs_needing_scraping()
        unscraped_urls = [job['job_url'] for job in unscraped_after]
        assert job_url not in unscraped_urls
        
        # Verify complete workflow state
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        
        # Check discovery record
        cursor.execute("SELECT COUNT(*) FROM job_discoveries WHERE job_url = ?", (job_url,))
        assert cursor.fetchone()[0] == 1
        
        # Check tracking record
        cursor.execute("SELECT detail_scraped FROM job_tracking WHERE job_url = ?", (job_url,))
        assert cursor.fetchone()[0] == 1  # True
        
        # Check job posting record
        cursor.execute("SELECT COUNT(*) FROM job_postings WHERE source_url = ?", (job_url,))
        assert cursor.fetchone()[0] == 1
        
        cursor.close()