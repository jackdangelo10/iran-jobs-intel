# src/parallel/worker_pool.py
"""
Worker pool manager for parallel job scraping.
Orchestrates multiple worker threads with shared queue and rate limiting.
"""
from __future__ import annotations
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from .job_queue import JobQueue
from .worker import ScrapeWorker
from ..scrapers.base.rate_limiter import RateLimiterRegistry

if TYPE_CHECKING:
    from typing import Type, Any

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Manages a pool of workers for parallel job scraping.
    
    Coordinates:
    - Thread-safe job queue
    - Per-site rate limiters
    - Worker threads
    - Progress tracking
    
    Example:
        pool = WorkerPool(
            database_conninfo="postgresql://...",
            session_id="uuid",
            num_workers=6,
            rate_limits={'irantalent': 20, 'jobinja': 15, 'jobvision': 20},
            scraper_classes={
                'IranTalentScraper': IranTalentScraper,
                'JobinjaScraper': JobinjaScraper,
                'JobVisionScraper': JobVisionScraper
            }
        )
        
        # Add jobs to queue
        pool.add_jobs(jobs_list)
        
        # Start parallel scraping
        results = pool.run()
    """
    
    def __init__(
        self,
        database_conninfo: str,
        session_id: str,
        num_workers: int,
        rate_limits: dict[str, int],
        scraper_classes: dict[str, Type]
    ):
        """
        Initialize worker pool.
        
        Args:
            database_conninfo: PostgreSQL connection string
            session_id: Current scraping session UUID
            num_workers: Number of parallel workers to run
            rate_limits: Dict mapping site names to requests_per_minute
                Example: {'irantalent': 20, 'jobinja': 15}
            scraper_classes: Dict mapping class names to scraper classes
                Example: {'IranTalentScraper': IranTalentScraper}
        """
        self.database_conninfo = database_conninfo
        self.session_id = session_id
        self.num_workers = num_workers
        
        # Create shared components
        self.job_queue = JobQueue()
        self.rate_limiter_registry = RateLimiterRegistry(rate_limits)
        self.scraper_classes = scraper_classes
        
        logger.info(
            f"Initialized WorkerPool: {num_workers} workers, "
            f"rate limits: {rate_limits}"
        )
    
    def add_jobs(self, jobs: list[dict[str, str]]) -> int:
        """
        Add jobs to the queue for scraping.
        
        Args:
            jobs: List of job dicts with keys:
                - job_url: URL of job detail page
                - source_site: Site identifier
                - scraper_class_name: Name of scraper class to use
        
        Returns:
            Number of jobs added
        """
        return self.job_queue.add_jobs_bulk(jobs)
    
    def run(self) -> dict[str, Any]:
        """
        Start parallel scraping and wait for completion.
        
        Creates worker threads, monitors progress, and returns results.
        
        Returns:
            Dict with:
                - total_jobs: Total jobs processed
                - successful: Successfully scraped jobs
                - failed: Failed jobs
                - workers: Per-worker statistics
                - duration_seconds: Total runtime
        """
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info(f"🚀 Starting parallel scraping with {self.num_workers} workers")
        logger.info("=" * 80)
        
        # Create workers
        workers = [
            ScrapeWorker(
                worker_id=i + 1,
                job_queue=self.job_queue,
                rate_limiter_registry=self.rate_limiter_registry,
                database_conninfo=self.database_conninfo,
                session_id=self.session_id,
                scraper_classes=self.scraper_classes
            )
            for i in range(self.num_workers)
        ]
        
        # Start progress monitoring in background thread
        monitor_thread = threading.Thread(
            target=self._monitor_progress,
            daemon=True
        )
        monitor_thread.start()
        
        # Run workers in thread pool
        worker_results = []
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all workers
            futures = {
                executor.submit(worker.run): worker
                for worker in workers
            }
            
            # Wait for completion and collect results
            for future in as_completed(futures):
                worker = futures[future]
                try:
                    result = future.result()
                    worker_results.append(result)
                except Exception as e:
                    logger.error(
                        f"Worker {worker.worker_id} failed with error: {e}",
                        exc_info=True
                    )
                    worker_results.append({
                        'worker_id': worker.worker_id,
                        'completed': 0,
                        'failed': 0,
                        'error': str(e)
                    })
        
        # Calculate final statistics
        duration = time.time() - start_time
        stats = self.job_queue.get_stats()
        
        results = {
            'total_jobs': stats.total_jobs,
            'successful': stats.completed_jobs - stats.failed_jobs,
            'failed': stats.failed_jobs,
            'success_rate': stats.success_rate,
            'workers': worker_results,
            'duration_seconds': duration
        }
        
        logger.info("=" * 80)
        logger.info(f"✅ Parallel scraping complete!")
        logger.info(f"   Total jobs: {stats.total_jobs}")
        logger.info(f"   Successful: {results['successful']}")
        logger.info(f"   Failed: {stats.failed_jobs}")
        logger.info(f"   Success rate: {stats.success_rate:.1f}%")
        logger.info(f"   Duration: {duration:.1f} seconds")
        logger.info(f"   Throughput: {stats.total_jobs / duration:.1f} jobs/sec")
        logger.info("=" * 80)
        
        return results
    
    def _monitor_progress(self):
        """
        Background thread that monitors and logs progress.
        Runs until queue is empty.
        """
        last_log_time = time.time()
        log_interval = 30  # Log every 30 seconds
        
        while not self.job_queue.is_empty():
            current_time = time.time()
            
            if current_time - last_log_time >= log_interval:
                stats = self.job_queue.get_stats()
                rate_stats = self.rate_limiter_registry.get_all_stats()
                
                logger.info("-" * 60)
                logger.info(f"📊 Progress Update:")
                logger.info(f"   {stats}")
                
                # Log rate limiter utilization
                for site, rl_stats in rate_stats.items():
                    logger.info(
                        f"   {site}: {rl_stats['requests_in_window']}/{rl_stats['capacity']} "
                        f"requests in window ({rl_stats['utilization_percent']:.0f}% utilization)"
                    )
                
                logger.info("-" * 60)
                last_log_time = current_time
            
            time.sleep(5)  # Check every 5 seconds