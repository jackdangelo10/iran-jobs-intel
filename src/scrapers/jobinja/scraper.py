# src/scrapers/jobinja/scraper.py
from __future__ import annotations
from turtle import title
from typing import List, Dict, Any, Optional
import requests
from src.scrapers.base.base_scraper import BaseScraper
import time
from bs4 import BeautifulSoup, soup

class JobinjaScraper(BaseScraper):

    def __init__(self, database, session_id: str):
        super().__init__(database, session_id)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Site URLs - we'll need to discover these
        self.base_url = "https://jobinja.ir/"
        self.jobs_list_url = "https://jobinja.ir/jobs"  # You'll tell me what this should be
        
        # Request settings
        self.request_delay = 2  # Seconds between requests
    
    def get_source_site(self) -> str:
        return "jobinja"
    
    def discover_job_urls(self) -> List[str]:
        """Paginate through job search pages and collect job URLs"""
        all_job_urls = []
        page = 1

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
        return "متاسفانه‌ برای فیلتر‌های اعمال شده نتیجه‌ای یافت نشد" in html
    

    def _extract_job_urls_from_page(self, html: str) -> List[str]:
        """Extract job URLs from job listing page HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        job_urls = []
        
        # Find all job card links based on the structure you provided
        # Select job title links in the new structure
        job_links = soup.select('a.c-jobListView__titleLink[href]')
        
        for link in job_links:
            href = link.get('href')
            if href:
                href = str(href)  
                if href.startswith("http"):
                    full_url = href
                else:
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
            
            # Extract job title
            title_elem = soup.select_one('div.c-jobView__titleText h1')
            title = title_elem.get_text().strip() if title_elem else None
            print(f"Job Title: {title}")
            
            # Extract company name and URL
            company_elem = soup.select_one('h2.c-companyHeader__name')
            company_name = company_elem.get_text().strip() if company_elem else None
            
            # Extract company name and URL
            company_elem = soup.select_one('h2.c-companyHeader__name')
            company_name = company_elem.get_text().strip() if company_elem else None

            company_url_elem = soup.select_one('a.c-companyHeader__logoLink[href]')
            company_url = str(company_url_elem.get('href')) if company_url_elem and company_url_elem.get('href') else None
            print(f"Company: {company_name}, URL: {company_url}")

            if company_url:
                self.database.companies.track_company_discovery(
                    company_url, self.source_site, self.session_id
                )
            # Extract location
            location_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Location")) .tags span.black')
            location = location_elem.get_text().strip() if location_elem else None
            print(f"Location: {location}")
            
            # Extract job description
            desc_elem = soup.select_one('h4:contains("Job description") + div.o-box__text')
            description = desc_elem.get_text().strip() if desc_elem else None
            
            # Extract employment type
            employment_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Type of cooperation")) .tags span.black')
            employment_type = employment_elem.get_text().strip().lower().replace(' ', '_') if employment_elem else 'unknown'
            print(f"Employment Type: {employment_type}")
            
            # Extract experience level
            experience_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Minimum work experience")) .tags span.black')
            experience_level = experience_elem.get_text().strip().lower().replace(' ', '_') if experience_elem else 'unknown'
            print(f"Experience Level: {experience_level}")
            
            # Extract education level - handle "مهم‌ نیست" case
            education_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Minimum educational qualification")) .tags span.black')
            if education_elem:
                education_text = education_elem.get_text().strip()
                if education_text == 'مهم‌ نیست':
                    education_level = 'none'  # Or 'any' - depends on how you want to categorize it
                else:
                    education_level = education_text
            else:
                education_level = 'unknown'
            print(f"Education Level: {education_level}")

            # Extract skills
            skills_elems = soup.select('li.c-infoBox__item:has(h4:contains("Required skills")) .tags span.black')
            skills_required = [skill.get_text().strip() for skill in skills_elems] if skills_elems else []
            print(f"Skills: {skills_required}")
            
            # Extract salary
            salary_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Rights")) .tags span.black')
            salary_raw = salary_elem.get_text().strip() if salary_elem else None
            print(f"Salary: {salary_raw}")
            
            # Generate external ID from URL
            external_id = job_url.split('/')[-1] if '/' in job_url else None
            print(f"External ID: {external_id}")


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


            # Extract gender requirement - Jobinja has explicit gender field
            gender_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Gender")) .tags span.black')
            if gender_elem:
                gender_text = gender_elem.get_text().strip()
                if gender_text in ['Woman', 'female', 'زن', 'خانم']:
                    gender_requirement = 'female'
                elif gender_text in ['Man', 'male', 'مرد', 'آقا']:
                    gender_requirement = 'male'
                elif gender_text == 'مهم‌ نیست':
                    gender_requirement = 'any'
                else:
                    gender_requirement = 'not_specified'
            else:
                gender_requirement = 'not_specified'

            print(f"Gender Requirement: {gender_requirement}")
            
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
                'employment_type': employment_type,
                'experience_level': experience_level,
                'gender_requirement': gender_requirement,
                'education_level': education_level,  # New field
                'salary_raw': salary_raw,  # New field  
                'skills_required': skills_required,  # New field
                'processing_status': 'pending'
            }
            
        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return {}
        
        return job_data
    
