# src/scrapers/jobvision/scraper.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import requests
from src.scrapers.base.base_scraper import BaseScraper
import time
from bs4 import BeautifulSoup, soup
from urllib.parse import urljoin

class JobVisionScraper(BaseScraper):

    def __init__(self, database, session_id: str):
        super().__init__(database, session_id)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Site URLs - we'll need to discover these
        self.base_url = "https://jobvision.ir/"
        self.jobs_list_url = "https://jobvision.ir/jobs"  # You'll tell me what this should be
        
        # Request settings
        self.request_delay = 2  # Seconds between requests

    def get_source_site(self) -> str:
        return "jobvision"
    
    def discover_job_urls(self) -> List[str]:
        """Paginate through job search pages and collect job URLs"""
        all_job_urls = []
        page = 1

        while True:
            page_url = f"{self.jobs_list_url}?page={page}"
            while True:
                page_url = f"{self.jobs_list_url}?page={page}"
                print(f"Scraping page {page}: {page_url}")

                try:
                    response = self.session.get(page_url, timeout=20)
                    # Save raw HTML
                    scrape_id = self.database.scrapes.save_raw_scrape(
                        source_site=self.source_site,
                        source_url=page_url,
                        page_type="job_list", 
                        scrape_session_id=self.session_id,
                        raw_html=response.text,
                        response_status=response.status_code
                    )

                    # Check if we've reached the end
                    if self._is_no_results_page(response.text):
                        print(f"No more results found at page {page}")
                        break

                    # Parse job URLs from this page
                    page_job_urls = self._extract_job_urls_from_page(response.text)
                    all_job_urls.extend(page_job_urls)

                    print(f"Found {len(page_job_urls)} jobs on page {page}")
                    
                    # Polite delay
                    time.sleep(self.request_delay)
                    page += 1

                except Exception as e:
                    print(f"Error fetching page {page}: {e}")
                    break

            return all_job_urls
    
    def _is_no_results_page(self, html: str) -> bool:
        """Check if page shows 'no jobs found' message"""
        return "فرصت شغلی برای جستجوی شما پیدا نشد" in html
    

    def _extract_job_urls_from_page(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select('a[href^="/jobs/"]')
        urls: List[str] = []
        seen = set()

        for a in anchors:
            href = a.get("href")
            if not href:
                continue
            # Force Pylance to see it as a string
            href_str = str(href)

            abs_url = urljoin(self.base_url, href_str)
            if abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)

        return urls
    
    
    def scrape_job_detail(self, job_url: str) -> Dict[str, Any]:

        return {}
