# src/scrapers/irantalent/scraper.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import requests
from src.scrapers.base.base_scraper import BaseScraper
import time
from bs4 import BeautifulSoup

class IranTalentScraper(BaseScraper):

    def __init__(self, database, session_id: str):
        super().__init__(database, session_id)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Site URLs - we'll need to discover these
        self.base_url = "https://irantalent.com"
        self.jobs_list_url = "https://www.irantalent.com/en/jobs/search"  # You'll tell me what this should be
        
        # Request settings
        self.request_delay = 2  # Seconds between requests

    def get_source_site(self) -> str:
        return "irantalent"
    
    def discover_job_urls(self) -> List[str]:
        """Paginate through job search pages and collect job URLs"""
        all_job_urls = []
        page = 1

        while True:
            page_url = f"{self.jobs_list_url}?language=english&page={page}"
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
                print(f"Error scraping page {page}: {e}")
                break


        return all_job_urls
    
    def _is_no_results_page(self, html: str) -> bool:
        """Check if page shows 'no jobs found' message"""
        return "Your filtered search does not match any jobs" in html 
    
    def _extract_job_urls_from_page(self, html: str) -> List[str]:
        """Extract job URLs from job listing page HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        job_urls = []
        
        # Find all job card links based on the structure you provided
        job_links = soup.select('new-position-card a[href^="/en/job/"]')
        
        for link in job_links:
            href = link.get('href')
            if href:
                full_url = f"{self.base_url}{href}"
                job_urls.append(full_url)
        
        return job_urls
    


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

            title_elem = soup.select_one('h1.margin-bottom-8.font-20.inline-middle.font-weight-500')
            title = title_elem.get_text().strip() if title_elem else None
            print(f"Job Title: {title}")

            company_elem = soup.select_one('a[href^="/en/company/"]')
            company_name = company_elem.get_text().strip() if company_elem else None
            company_url = f"{self.base_url}{company_elem.get('href')}" if company_elem else None
            print(f"Company: {company_name}, URL: {company_url}")

            # Extract location
            location_elem = soup.select_one('span.color-gray')
            location = location_elem.get_text().strip() if location_elem else None
            print(f"Location: {location}")

            # Extract job description
            desc_elem = soup.select_one('p.description.margin-top-12.margin-bottom-8.pre-wrap.text-start')
            description = desc_elem.get_text().strip() if desc_elem else None

            # Extract employment type
            employment_elem = soup.select_one('div.margin-y-8 ul li.description')
            employment_type = employment_elem.get_text().strip().lower().replace(' ', '_') if employment_elem else 'unknown'
            print(f"Employment Type: {employment_type}")

            # Generate external ID from URL
            external_id = job_url.split('/')[-1] if '/' in job_url else None
            print(f"External ID: {external_id}")

            # Extract experience level/seniority
            seniority_elem = soup.select_one('div.margin-y-8 p:contains("Seniority") + ul li a')
            experience_level = seniority_elem.get_text().strip().lower().replace(' ', '_') if seniority_elem else 'unknown'
            print(f"Experience Level: {experience_level}")

            # Extract posted date
            posted_elem = soup.select_one('p.text-sm.margin-right-16')
            posted_date_raw = posted_elem.get_text().strip() if posted_elem else None




            job_data = {
                'raw_scrape_id': scrape_id,
                'external_id': external_id,
                'source_site': self.source_site,
                'source_url': job_url,
                'title_persian': title,  # Could be English, we'll detect language later
                'description_persian': description,
                'company_name_raw': company_name,
                'location_raw': location,
                'employment_type': employment_type,
                'experience_level': experience_level,  # "experienced_professional"
                'posted_date': posted_date_raw,
                'processing_status': 'pending'
            }

        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return {}
        
        return job_data