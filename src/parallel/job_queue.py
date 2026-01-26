# src/parallel/job_queue.py
"""
Thread-safe job queue for distributing scraping tasks to workers.
"""
from __future__ import annotations
import queue
import logging
from typing import TypedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class JobItem(TypedDict):
    """Job queue item structure."""
    job_url: str
    source_site: str
    scraper_class_name: str  # Class name string for dynamic import


@dataclass
class JobQueueStats:
    """Statistics for job queue."""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    remaining_jobs: int
    success_rate: float
    
    def __str__(self) -> str:
        return (
            f"JobQueue Stats: "
            f"{self.completed_jobs}/{self.total_jobs} completed "
            f"({self.success_rate:.1f}% success), "
            f"{self.remaining_jobs} remaining, "
            f"{self.failed_jobs} failed"
        )


class JobQueue:
    """
    Thread-safe queue for distributing scraping jobs to workers.
    
    Manages the queue of jobs to be scraped and tracks completion statistics.
    
    Example:
        queue = JobQueue()
        
        # Producer: Add jobs
        queue.add_job(job_url="...", source_site="irantalent", ...)
        
        # Consumer (worker): Get and complete jobs
        job = queue.get_job(timeout=1.0)
        if job:
            # ... scrape job ...
            queue.mark_completed(job, success=True)
    """
    
    def __init__(self):
        """Initialize empty job queue."""
        self._queue: queue.Queue[JobItem] = queue.Queue()
        self._total_jobs = 0
        self._completed_jobs = 0
        self._failed_jobs = 0
    
    def add_job(
        self,
        job_url: str,
        source_site: str,
        scraper_class_name: str
    ) -> None:
        """
        Add a job to the queue.
        
        Args:
            job_url: URL of job to scrape
            source_site: Site identifier (irantalent, jobinja, jobvision)
            scraper_class_name: Name of scraper class (for dynamic import)
        """
        job_item: JobItem = {
            'job_url': job_url,
            'source_site': source_site,
            'scraper_class_name': scraper_class_name
        }
        
        self._queue.put(job_item)
        self._total_jobs += 1
    
    def add_jobs_bulk(self, jobs: list[dict[str, str]]) -> int:
        """
        Add multiple jobs at once.
        
        Args:
            jobs: List of job dicts with keys: job_url, source_site, scraper_class_name
            
        Returns:
            Number of jobs added
        """
        for job in jobs:
            self.add_job(
                job_url=job['job_url'],
                source_site=job['source_site'],
                scraper_class_name=job['scraper_class_name']
            )
        
        logger.info(f"Added {len(jobs)} jobs to queue")
        return len(jobs)
    
    def get_job(self, timeout: float = 1.0) -> JobItem | None:
        """
        Get next job from queue (blocking with timeout).
        
        Args:
            timeout: How long to wait for a job (seconds)
            
        Returns:
            JobItem or None if queue is empty after timeout
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def mark_completed(self, job: JobItem, success: bool = True) -> None:
        """
        Mark a job as completed.
        
        Args:
            job: The job that was completed
            success: Whether job completed successfully
        """
        self._queue.task_done()
        self._completed_jobs += 1
        
        if not success:
            self._failed_jobs += 1
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def size(self) -> int:
        """Get current queue size (approximate)."""
        return self._queue.qsize()
    
    def get_stats(self) -> JobQueueStats:
        """
        Get current queue statistics.
        
        Returns:
            JobQueueStats with completion metrics
        """
        remaining = self._total_jobs - self._completed_jobs
        success_rate = (
            ((self._completed_jobs - self._failed_jobs) / self._completed_jobs * 100)
            if self._completed_jobs > 0
            else 0.0
        )
        
        return JobQueueStats(
            total_jobs=self._total_jobs,
            completed_jobs=self._completed_jobs,
            failed_jobs=self._failed_jobs,
            remaining_jobs=remaining,
            success_rate=success_rate
        )
    
    def wait_for_completion(self, timeout: float | None = None) -> bool:
        """
        Block until all jobs are completed.
        
        Args:
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if all jobs completed, False if timeout
        """
        try:
            self._queue.join()
            return True
        except:
            return False