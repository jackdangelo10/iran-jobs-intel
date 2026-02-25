# src/scrapers/base/base_scraper.py
"""
Base scraper class with support for parallel execution and rate limiting.

REFACTORED for parallel scraping:
- Lazy driver initialization (create on-demand)
- Rate limiter integration
- Cleaner resource management
"""
from abc import ABC, abstractmethod
from typing import List, Literal
from src.database import IranJobsDB
from src.database.models import JobPosting
from src.scrapers.base.rate_limiter import RateLimiterRegistry
from src.scrapers.base.driver_manager import DriverManager
from src.config.settings import settings
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

ScrapingMethod = Literal["requests", "selenium"]


class BaseScraper(ABC):
    """
    Base class for all site-specific scrapers.
    
    IMPORTANT CHANGES FOR PARALLEL SCRAPING:
    - No longer creates driver in __init__ (lazy initialization)
    - Accepts rate_limiter_registry for coordination
    - Driver created per job (in scrape_job_detail)
    - Automatic rate limiting before each request
    
    Subclasses must implement:
    - get_source_site() -> str
    - discover_job_urls() -> List[str]
    - scrape_job_detail(job_url) -> JobPosting | None
    """

    def __init__(
        self,
        database: IranJobsDB,
        session_id: str,
        method: ScrapingMethod = "requests",
        rate_limiter_registry: RateLimiterRegistry | None = None
    ):
        """
        Initialize scraper.
        
        Args:
            database: Database connection
            session_id: Current scraping session UUID
            method: Scraping method (requests or selenium)
            rate_limiter_registry: Optional registry for parallel coordination
        """
        self.database = database
        self.session_id = session_id
        self.source_site = self.get_source_site()
        self.scraping_method = method
        self.rate_limiter_registry = rate_limiter_registry
        
        # Driver is created on-demand, not in __init__
        self.driver: webdriver.Chrome | None = None
        self.wait: WebDriverWait | None = None
        
        # Session for requests method
        if method == "requests":
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/120.0.0.0 Safari/537.36'
            })
        else:
            self.session = None

    def _get_or_create_driver(self) -> webdriver.Chrome:
        """
        Get existing driver or create new one (lazy initialization).
        
        Returns:
            Selenium WebDriver instance
        """
        if self.driver is None:
            self.driver = DriverManager.create_driver(
                headless=True,
                timeout=settings.page_load_timeout,
                page_load_strategy="eager"
            )
            self.wait = WebDriverWait(self.driver, settings.page_load_timeout)
        
        return self.driver
    
    def _apply_rate_limit(self):
        """
        Apply rate limiting before making a request.
        
        If rate_limiter_registry is set (parallel mode), coordinates
        with other workers. Otherwise, no rate limiting.
        """
        if self.rate_limiter_registry:
            limiter = self.rate_limiter_registry.get_limiter(self.source_site)
            wait_time = limiter.wait_if_needed()
            
            if wait_time > 0:
                print(f"  ⏱️  Rate limited: waited {wait_time:.1f}s")
    
    def get_page_content(self, url: str, timeout: int = 20) -> tuple[str, int]:
        """
        Get page content using the configured method.
        
        Automatically applies rate limiting if in parallel mode.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (HTML content, HTTP status code)
        """
        # Apply rate limiting BEFORE making request
        self._apply_rate_limit()
        
        if self.scraping_method == "requests":
            if not self.session:
                raise RuntimeError("Session not initialized for requests method")
            response = self.session.get(url, timeout=timeout)
            return response.text, response.status_code
        
        elif self.scraping_method == "selenium":
            driver = self._get_or_create_driver()
            driver.get(url)
            self._wait_for_page_load()
            return driver.page_source, 200
        
        else:
            raise ValueError(f"Unknown scraping method: {self.scraping_method}")
    
    def _wait_for_page_load(self):
        """
        Override this in subclasses for site-specific wait conditions.
        Default implementation waits 2 seconds.
        """
        import time
        time.sleep(2)
    
    def cleanup(self):
        """
        Clean up resources (Selenium driver, requests session).
        
        IMPORTANT: Always call this when done with scraper, especially
        in parallel mode where drivers are created per job.
        """
        if self.driver:
            DriverManager.cleanup_driver(self.driver)
            self.driver = None
            self.wait = None
        
        if self.session:
            self.session.close()
            self.session = None
    
    @abstractmethod
    def get_source_site(self) -> str:
        """
        Return the site identifier (irantalent, jobvision, jobinja).
        
        Returns:
            Site identifier string
        """
        pass
    
    @abstractmethod
    def discover_job_urls(self) -> List[str]:
        """
        Scrape job listing pages and return discovered job URLs.
        
        This method is called during Phase 1 (Discovery) and should
        paginate through search results to find all job URLs.
        
        Returns:
            List of job detail page URLs
        """
        pass
    
    @abstractmethod
    def scrape_job_detail(self, job_url: str) -> JobPosting | None:
        """
        Scrape individual job detail page and return JobPosting model.
        
        This method is called during Phase 2 (Parallel Detail Scraping)
        by worker threads. Each call should:
        1. Fetch job detail page (rate limiting handled automatically)
        2. Extract all relevant information
        3. Return validated JobPosting model
        
        Args:
            job_url: URL of job detail page to scrape
            
        Returns:
            JobPosting model if successful, None if failed
        """
        pass
    
    def run_scraping_session(self) -> dict[str, int]:
        """
        Main workflow orchestration - SEQUENTIAL MODE ONLY.
        
        This method is used when running a single scraper sequentially
        (not in parallel mode). For parallel mode, use WorkerPool instead.
        
        Returns:
            Dict with discovery and scraping statistics
        """
        try:
            print(f"Starting {self.source_site} scraping session: {self.session_id}")
            
            # Step 1: Discover job URLs by paginating
            job_urls = self.discover_job_urls()
            print(f"Discovered {len(job_urls)} job URLs")

            # Remove duplicates
            unique_job_urls = list(dict.fromkeys(job_urls))
            if len(unique_job_urls) != len(job_urls):
                print(f"Removed {len(job_urls) - len(unique_job_urls)} duplicate URLs")
            
            # Step 2: Record discoveries and update tracking
            for job_url in unique_job_urls:
                self.database.jobs.record_job_discovery(
                    self.session_id, job_url, self.source_site
                )
                self.database.jobs.update_job_tracking(
                    job_url, self.source_site, self.session_id
                )
            
            # Step 3: Get jobs needing detail scraping
            unscraped_jobs = self.database.jobs.get_jobs_needing_scraping()
            
            # Step 4: Scrape job details (SEQUENTIAL)
            scraped_count = 0
            failed_count = 0
            
            for job in unscraped_jobs:
                try:
                    job_posting = self.scrape_job_detail(job['job_url'])
                    if job_posting:
                        self.database.jobs.save_job_posting(job_posting)
                        self.database.jobs.mark_job_scraped(job['job_url'], success=True)
                        scraped_count += 1
                    else:
                        self.database.jobs.mark_job_scraped(job['job_url'], success=False)
                        failed_count += 1
                except Exception as e:
                    print(f"Failed to scrape {job['job_url']}: {e}")
                    self.database.jobs.mark_job_scraped(job['job_url'], success=False)
                    failed_count += 1
            
            return {
                'discovered': len(job_urls),
                'scraped': scraped_count,
                'failed': failed_count
            }
    
        finally:
            # Always cleanup
            self.cleanup()
