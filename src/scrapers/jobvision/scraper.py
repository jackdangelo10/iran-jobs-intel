# src/scrapers/jobvision/scraper.py
from __future__ import annotations
from typing import List
from src.scrapers.base.base_scraper import BaseScraper
from src.database.models import JobPosting
from datetime import date
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class JobVisionScraper(BaseScraper):

    def __init__(self, database, session_id: str):
        # Force Selenium for JobVision
        super().__init__(database, session_id, method="selenium")

        # Site URLs
        self.base_url = "https://jobvision.ir/"
        self.jobs_list_url = "https://jobvision.ir/jobs"
        
        # Request settings
        self.request_delay = 2  # Seconds between requests

    def get_source_site(self) -> str:
        return "jobvision"
    
    def _wait_for_page_load(self):
        """Wait for job listings to load"""
        try:
            if self.wait:
                # Wait for job links to appear
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/jobs/"]')))
        except:
            # If no job links found, might be end of results
            pass
    
    def discover_job_urls(self) -> List[str]:
        """Paginate through job search pages and collect job URLs"""
        all_job_urls = []
        page = 1

        while True:
            page_url = f"{self.jobs_list_url}?page={page}"
            print(f"Scraping page {page}: {page_url}")

            try:
                html, status_code = self.get_page_content(page_url)
                print(f"Status Code: {status_code}")
                
                if status_code != 200:
                    print(f"Failed to retrieve page {page}")
                    break

                # Save raw HTML
                scrape_id = self.database.scrapes.save_raw_scrape(
                    source_site=self.source_site,
                    source_url=page_url,
                    page_type="job_list", 
                    scrape_session_id=self.session_id,
                    raw_html=html,
                    response_status=status_code
                )

                # Check if we've reached the end
                if self._is_no_results_page(html):
                    print(f"No more results found at page {page}")
                    break

                # Parse job URLs from this page
                page_job_urls = self._extract_job_urls_from_page(html)
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
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check if the empty state component is actually visible/active
        empty_state = soup.select_one('app-empty-state.ng-star-inserted')
        if empty_state:
            # Check if it has display content (not just ng-star-inserted)
            # The empty state is shown when there are actually no results
            return 'فرصت شغلی برای جستجوی شما پیدا نشد' in empty_state.get_text()
        
        # Also check if there are any job cards - if yes, definitely not empty
        job_cards = soup.select('a[href^="/jobs/"]')
        return len(job_cards) == 0
    
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
    
    def scrape_job_detail(self, job_url: str) -> JobPosting | None:
        """Scrape individual job detail page and return JobPosting model"""
        try:
            html, status_code = self.get_page_content(job_url)
            print(f"Scraping job detail: {job_url} (Status: {status_code})")
            
            if status_code != 200:
                print(f"Failed to retrieve job detail page: {job_url}")
                return None
            
            # Save raw HTML
            scrape_id = self.database.scrapes.save_raw_scrape(
                source_site=self.source_site,
                source_url=job_url,
                page_type="job_detail", 
                scrape_session_id=self.session_id,
                raw_html=html,
                response_status=status_code
            )
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract job title
            title_elem = soup.select_one('h1.text-black.font-size-1.font-weight-bold.py-2.yn*title')
            title = title_elem.get_text().strip() if title_elem else None
            
            # Extract company name and URL
            company_elem = soup.select_one('a.text-primary.font-size-2.font-weight-bold.yn_brand')
            company_name = company_elem.get_text().strip() if company_elem else None
            
            company_url = None
            if company_elem and company_elem.get('href'):
                href = str(company_elem.get('href'))
                if href.startswith('/'):
                    company_url = f"{self.base_url}{href}"
                else:
                    company_url = href
            
            if company_url:
                self.database.companies.track_company_discovery(
                    company_url, self.source_site, self.session_id
                )
            
            # Extract location
            location_elem = soup.select_one('span.text-muted.font-size-6.yn*category')
            location = location_elem.get_text().strip() if location_elem else None
            
            # Extract job description
            desc_elem = soup.select_one('h2:contains("Job description and duties") + div')
            description = desc_elem.get_text().strip() if desc_elem else None
            
            # Extract gender requirement
            gender_elem = soup.select_one('div.requirement-value.text-black.bg-light')
            gender_requirement = 'not_specified'
            if gender_elem:
                gender_text = gender_elem.get_text().strip()
                if gender_text in ['There is no difference.', 'تفاوت ندارد', 'مهم نیست']:
                    gender_requirement = 'any'
                elif 'woman' in gender_text.lower() or 'female' in gender_text.lower() or 'زن' in gender_text or 'خانم' in gender_text:
                    gender_requirement = 'female'
                elif 'man' in gender_text.lower() or 'male' in gender_text.lower() or 'مرد' in gender_text or 'آقا' in gender_text:
                    gender_requirement = 'male'
            
            # Generate external ID from URL
            external_id = job_url.split('/')[-1] if '/' in job_url else None
            
            # Create JobPosting model with validation
            today = date.today()
            
            job_posting = JobPosting(
                raw_scrape_id=scrape_id,
                external_id=external_id,
                source_site=self.source_site,
                source_url=job_url,
                title_persian=title or "",  # Required field
                description_persian=description,
                company_name_raw=company_name,
                company_url=company_url,
                location_raw=location,
                gender_requirement=gender_requirement,
                processing_status='pending',
                first_seen_date=today,
                last_seen_date=today
            )
            
            print(f"✅ Created JobPosting model for: {title}")
            return job_posting
            
        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return None