# src/scrapers/irantalent/scraper.py
from __future__ import annotations
from typing import List, Dict, Any
from src.scrapers.base.base_scraper import BaseScraper
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class IranTalentScraper(BaseScraper):

    def __init__(self, database, session_id: str):
        # Force Selenium for IranTalent since it's an Angular SPA
        super().__init__(database, session_id, method="selenium")

        # Site URLs - we'll need to discover these
        self.base_url = "https://irantalent.com"
        self.jobs_list_url = "https://www.irantalent.com/en/jobs/search"  # You'll tell me what this should be
        
        # Request settings
        self.request_delay = 2  # Seconds between requests

    def get_source_site(self) -> str:
        return "irantalent"
    
    def _wait_for_page_load(self):
        """Wait for job cards to load"""
        try:
            if self.wait:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "new-position-card")))
        except:
            # If no job cards found, might be end of results
            pass
    
    def discover_job_urls(self) -> List[str]:
        """Paginate through job search pages and collect job URLs"""
        all_job_urls = []
        page = 1

        while True:
            page_url = f"{self.jobs_list_url}?language=english&page={page}"
            print(f"Scraping page {page}: {page_url}")
            try:
                html, status_code = self.get_page_content(page_url)
                print(f"Status Code: {status_code}")
                if status_code != 200:
                    print(f"Failed to retrieve page {page}")
                    break
                with open("data/html_dumps/debug_irantalent_page.html", "w", encoding="utf-8") as f:
                    f.write(html)

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
            html, status_code = self.get_page_content(job_url)
            print(f"Scraping job detail: {job_url} (Status: {status_code})")
            if status_code != 200:
                print(f"Failed to retrieve job detail page: {job_url}")
                return {}
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

            title_elem = soup.select_one('h1.margin-bottom-8.font-20.inline-middle.font-weight-500')
            title = title_elem.get_text().strip() if title_elem else None
            print(f"Job Title: {title}")

            company_elem = soup.select_one('a[href^="/en/company/"]')
            company_name = company_elem.get_text().strip() if company_elem else None
            company_url = f"{self.base_url}{company_elem.get('href')}" if company_elem else None
            print(f"Company: {company_name}, URL: {company_url}")

            if company_url:
                self.database.companies.track_company_discovery(
                    company_url, self.source_site, self.session_id
                )

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

            # Extract gender requirement (check title and description)
            gender_requirement = 'not_specified'

            # Convert to lowercase safely
            title_text = (title or '').lower()
            description_text = (description or '').lower()

            if '(female)' in title_text or (title and 'خانم' in title) or 'female' in description_text:
                gender_requirement = 'female'
            elif '(male)' in title_text or (title and 'آقا' in title) or 'male' in description_text:
                gender_requirement = 'male'

            print(f"Gender Requirement: {gender_requirement}")


            job_data = {
                'raw_scrape_id': scrape_id,
                'external_id': external_id,
                'source_site': self.source_site,
                'source_url': job_url,
                'title_persian': title,  # Could be English, we'll detect language later
                'description_persian': description,
                'company_name_raw': company_name,
                'company_url': company_url, 
                'location_raw': location,
                'employment_type': employment_type,
                'experience_level': experience_level,  # "experienced_professional", can be normalized later
                'posted_date': posted_date_raw,
                'gender_requirement': gender_requirement,
                'processing_status': 'pending'
            }

        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return {}
        
        return job_data