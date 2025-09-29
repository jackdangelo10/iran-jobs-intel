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
        """Scrape individual job detail page and return structured data"""
        try:
            response = self.session.get(job_url, timeout=20)
            # Save raw HTML
            scrape_id = self.database.scrapes.save_raw_scrape(
                source_site=self.source_site,
                source_url=job_url,
                page_type="job_detail", 
                scrape_session_id=self.session_id,
                raw_html=response.text,
                response_status=response.status_code
            )
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract job title
            title_elem = soup.select_one('h1.text-black.font-size-1.font-weight-bold.py-2.yn*title')
            title = title_elem.get_text().strip() if title_elem else None
            print(f"Job Title: {title}")
            
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
            
            print(f"Company: {company_name}, URL: {company_url}")
            
            if company_url:
                self.database.companies.track_company_discovery(
                    company_url, self.source_site, self.session_id
                )
            
            # Extract location
            location_elem = soup.select_one('span.text-muted.font-size-6.yn*category')
            location = location_elem.get_text().strip() if location_elem else None
            print(f"Location: {location}")
            
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
            
            print(f"Gender Requirement: {gender_requirement}")
            
            # Generate external ID from URL
            external_id = job_url.split('/')[-1] if '/' in job_url else None
            print(f"External ID: {external_id}")
            
            job_data = {
                'raw_scrape_id': scrape_id,
                'external_id': external_id,
                'source_site': self.source_site,
                'source_url': job_url,
                'title_persian': title,
                'description_persian': description,
                'company_name_raw': company_name,
                'company_url': company_url,
                'location_raw': location,
                'gender_requirement': gender_requirement,
                'processing_status': 'pending'
            }
            
        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return {}
        
        return job_data
