from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.database import IranJobsDB


class BaseScraper(ABC):

    def __init__(self, database: IranJobsDB, session_id: str):
        self.database = database
        self.session_id = session_id
        self.source_site = self.get_source_site()
    
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
    
    def run_scraping_session(self, max_pages: int = 5) -> Dict[str, int]:
        """Main workflow orchestration - same for all scrapers"""
        
        print(f"Starting {self.source_site} scraping session: {self.session_id}")
        
        # Step 1: Discover job URLs by paginating on source url
        job_urls = self.discover_job_urls()
        print(f"Discovered {len(job_urls)} job URLs")
        
        # Step 2: Record discoveries and update tracking
        for job_url in job_urls:
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