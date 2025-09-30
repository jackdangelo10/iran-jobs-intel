from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal
from src.database import IranJobsDB
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ScrapingMethod = Literal["requests", "selenium"]

class BaseScraper(ABC):

    def __init__(self, database: IranJobsDB, session_id: str, method: ScrapingMethod = "requests"):
        self.database = database
        self.session_id = session_id
        self.source_site = self.get_source_site()
        self.scraping_method = method
        
        # Initialize the appropriate scraping tool
        if method == "requests":
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            self.driver = None
            self.wait = None
        elif method == "selenium":
            self.session = None
            self._setup_selenium()

    def _setup_selenium(self):
        """Initialize Selenium WebDriver with anti-detection settings"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Additional anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Remove webdriver property to avoid detection
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        # Increase timeout to 40 seconds for challenge pages
        self.wait = WebDriverWait(self.driver, 40)
    
    def get_page_content(self, url: str, timeout: int = 20) -> tuple[str, int]:
        """Get page content using the configured method"""
        if self.scraping_method == "requests":
            if not self.session:
                raise RuntimeError("Session not initialized for requests method")
            response = self.session.get(url, timeout=timeout)
            return response.text, response.status_code
        
        elif self.scraping_method == "selenium":
            if not self.driver:
                raise RuntimeError("WebDriver not initialized for selenium method")
            self.driver.get(url)
            self._wait_for_page_load()
            return self.driver.page_source, 200
        
        else:
            raise ValueError(f"Unknown scraping method: {self.scraping_method}")
    
    def _wait_for_page_load(self):
        """Override this in subclasses for site-specific wait conditions"""
        import time
        time.sleep(2)  # Default wait
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
    
    @abstractmethod
    def get_source_site(self) -> str:
        """Return the site identifier (irantalent, jobvision, etc.)"""
        pass
    
    @abstractmethod
    def discover_job_urls(self) -> List[str]:
        """Scrape job listing pages and return discovered job URLs"""
        pass
    
    @abstractmethod
    def scrape_job_detail(self, job_url: str) -> Dict[str, Any]:
        """Scrape individual job detail page and return structured data"""
        pass
    
    def run_scraping_session(self) -> Dict[str, int]:
        """Main workflow orchestration - same for all scrapers"""
        try:
        
            print(f"Starting {self.source_site} scraping session: {self.session_id}")
            
            # Step 1: Discover job URLs by paginating on source url
            job_urls = self.discover_job_urls()
            print(f"Discovered {len(job_urls)} job URLs")

            unique_job_urls = list(dict.fromkeys(job_urls))  # Preserves order, removes dupes
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
            
            # Step 4: Scrape job details
            scraped_count = 0
            failed_count = 0
            
            for job in unscraped_jobs:
                try:
                    job_data = self.scrape_job_detail(job['job_url'])
                    if job_data:
                        self.database.jobs.save_job_posting(job_data)
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
                # Always cleanup Selenium
                self.cleanup()