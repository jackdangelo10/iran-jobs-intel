# src/parallel/worker.py
"""
Individual worker thread for parallel job scraping.
"""
from __future__ import annotations
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .job_queue import JobQueue, JobItem
    from ..scrapers.base.rate_limiter import RateLimiterRegistry
    from ..database import IranJobsDB

logger = logging.getLogger(__name__)


class ScrapeWorker:
    """
    Individual worker that processes jobs from the queue.
    
    Each worker:
    1. Pulls jobs from shared queue
    2. Creates appropriate scraper for the job's site
    3. Coordinates with rate limiter
    4. Scrapes job detail
    5. Saves to database
    6. Repeats until queue empty
    
    Designed to run in its own thread with proper resource cleanup.
    """
    
    def __init__(
        self,
        worker_id: int,
        job_queue: JobQueue,
        rate_limiter_registry: RateLimiterRegistry,
        database_conninfo: str,
        session_id: str,
        scraper_classes: dict[str, type]
    ):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique identifier for this worker
            job_queue: Shared job queue
            rate_limiter_registry: Shared rate limiters per site
            database_conninfo: PostgreSQL connection string
            session_id: Current scraping session ID
            scraper_classes: Dict mapping class names to scraper classes
        """
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.rate_limiter_registry = rate_limiter_registry
        self.database_conninfo = database_conninfo
        self.session_id = session_id
        self.scraper_classes = scraper_classes
        
        # Worker statistics
        self.jobs_completed = 0
        self.jobs_failed = 0
        
        # Thread control
        self._stop_event = threading.Event()
    
    def run(self) -> dict[str, int]:
        """
        Main worker loop - processes jobs until queue is empty or stopped.
        
        Returns:
            Dict with worker statistics
        """
        logger.info(f"Worker {self.worker_id} starting...")
        
        # Import database here (thread-local)
        from ..database import IranJobsDB
        db = IranJobsDB(self.database_conninfo)
        
        try:
            while not self._stop_event.is_set():
                # Get next job from queue (with timeout so we can check stop_event)
                job = self.job_queue.get_job(timeout=1.0)
                
                if job is None:
                    # Queue is empty, we're done
                    logger.debug(f"Worker {self.worker_id}: Queue empty, finishing")
                    break
                
                # Process the job
                success = self._process_job(job, db)
                
                # Mark job as completed
                self.job_queue.mark_completed(job, success=success)
                
                if success:
                    self.jobs_completed += 1
                else:
                    self.jobs_failed += 1
            
            logger.info(
                f"Worker {self.worker_id} finished: "
                f"{self.jobs_completed} completed, {self.jobs_failed} failed"
            )
            
            return {
                'worker_id': self.worker_id,
                'completed': self.jobs_completed,
                'failed': self.jobs_failed
            }
            
        finally:
            # Always cleanup database connection
            db.close()
    
    def _process_job(self, job: JobItem, db: IranJobsDB) -> bool:
        """
        Process a single job.
        
        Args:
            job: Job to process
            db: Database connection
            
        Returns:
            True if successful, False if failed
        """
        job_url = job['job_url']
        source_site = job['source_site']
        scraper_class_name = job['scraper_class_name']
        
        logger.debug(
            f"Worker {self.worker_id}: Processing {source_site} job: {job_url}"
        )
        
        try:
            # Get scraper class
            if scraper_class_name not in self.scraper_classes:
                logger.error(
                    f"Worker {self.worker_id}: Unknown scraper class: {scraper_class_name}"
                )
                return False
            
            scraper_class = self.scraper_classes[scraper_class_name]
            
            # Create scraper instance for this job
            # Note: Each scraper gets rate_limiter_registry to coordinate
            scraper = scraper_class(
                database=db,
                session_id=self.session_id,
                rate_limiter_registry=self.rate_limiter_registry  # NEW PARAM
            )
            
            try:
                # Scrape job detail (rate limiting happens inside scraper)
                job_posting = scraper.scrape_job_detail(job_url)
                
                if job_posting:
                    # Save to database
                    db.jobs.save_job_posting(job_posting)
                    db.jobs.mark_job_scraped(job_url, success=True)
                    
                    logger.debug(
                        f"Worker {self.worker_id}: ✓ Scraped {source_site} job"
                    )
                    return True
                else:
                    # Scraping returned None (likely an error)
                    db.jobs.mark_job_scraped(job_url, success=False)
                    logger.warning(
                        f"Worker {self.worker_id}: ✗ Failed to scrape {source_site} job"
                    )
                    return False
                    
            finally:
                # Always cleanup scraper resources (Selenium driver)
                scraper.cleanup()
                
        except Exception as e:
            logger.error(
                f"Worker {self.worker_id}: Error processing {source_site} job: {e}",
                exc_info=True
            )
            
            try:
                db.jobs.mark_job_scraped(job_url, success=False)
            except:
                pass
            
            return False
    
    def stop(self):
        """Signal worker to stop gracefully."""
        self._stop_event.set()