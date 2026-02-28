# src/scrapers/irantalent/scraper.py
from __future__ import annotations
from typing import List
from src.scrapers.base.base_scraper import BaseScraper
from src.config.settings import settings
from src.database.models import JobPosting
from datetime import date
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC


class IranTalentScraper(BaseScraper):

    def __init__(self, database, session_id: str, rate_limiter_registry=None):
        # Force Selenium for IranTalent since it's an Angular SPA
        super().__init__(
            database,
            session_id,
            method="selenium",
            rate_limiter_registry=rate_limiter_registry
        )

        # Site URLs
        self.base_url = "https://irantalent.com"
        self.jobs_list_url = "https://www.irantalent.com/en/jobs/search"
        
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

    def _get_keywords(self) -> list[str]:
        if settings.water_focus_enabled:
            return settings.irantalent_water_keywords_en or ["water"]
        return [""]

    def _set_page(self, url: str, page: int) -> str:
        parsed = urlsplit(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["page"] = str(page)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    def _resolve_keyword_search_url(self, keyword: str) -> str:
        base_url = f"{self.jobs_list_url}?language=english"
        if not keyword:
            return base_url

        try:
            driver = self._get_or_create_driver()
            driver.get(base_url)
            self._wait_for_page_load()

            search_input = driver.find_element(By.CSS_SELECTOR, "input.advanced-search-placeholder")
            driver.execute_script(
                "arguments[0].removeAttribute('readonly'); arguments[0].value = '';",
                search_input,
            )
            search_input.send_keys(keyword)
            search_input.send_keys(Keys.ENTER)
            time.sleep(2)

            current_url = driver.current_url
            if current_url:
                return current_url
        except Exception as e:
            print(f"Keyword URL resolution failed for '{keyword}': {e}")

        fallback_query = urlencode({"language": "english", "keyword": keyword})
        return f"{self.jobs_list_url}?{fallback_query}"

    def discover_job_urls(self) -> List[str]:
        """Discover keyword-filtered job URLs and return deduped list."""
        all_job_urls: list[str] = []
        keywords = self._get_keywords()

        max_consecutive_errors = 3
        max_consecutive_seen_pages = settings.max_consecutive_seen_pages
        seen_ratio_threshold = settings.seen_ratio_threshold

        for keyword in keywords:
            search_url = self._resolve_keyword_search_url(keyword)
            label = keyword if keyword else "<all>"
            page = 1
            consecutive_errors = 0
            consecutive_seen_pages = 0

            print(f"\nSearching IranTalent keyword: {label}")

            while True:
                page_url = self._set_page(search_url, page)
                print(f"Scraping page {page}: {page_url}")
                try:
                    html, status_code = self.get_page_content(page_url)
                    print(f"Status Code: {status_code}")
                    if status_code != 200:
                        print(f"Failed to retrieve page {page}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print("Too many errors for this keyword. Moving on.")
                            break
                        time.sleep(self.request_delay)
                        continue

                    self.database.scrapes.save_raw_scrape(
                        source_site=self.source_site,
                        source_url=page_url,
                        page_type="job_list",
                        scrape_session_id=self.session_id,
                        raw_html=html,
                        response_status=status_code
                    )

                    if self._is_no_results_page(html):
                        print(f"No more results for keyword '{label}' at page {page}")
                        break

                    page_job_urls = self._extract_job_urls_from_page(html)
                    if len(page_job_urls) == 0:
                        print(f"No jobs found on page {page} for keyword '{label}'.")
                        break

                    all_job_urls.extend(page_job_urls)
                    print(f"Found {len(page_job_urls)} jobs on page {page}")
                    consecutive_errors = 0

                    if max_consecutive_seen_pages > 0:
                        seen_count, total_count, seen_ratio = self._seen_ratio_on_page(page_job_urls)
                        if total_count > 0 and seen_ratio >= seen_ratio_threshold:
                            consecutive_seen_pages += 1
                            print(f"Seen-only page streak: {consecutive_seen_pages}/{max_consecutive_seen_pages}")
                            if consecutive_seen_pages >= max_consecutive_seen_pages:
                                print("Too many consecutive seen-only pages for this keyword. Moving on.")
                                break
                        else:
                            consecutive_seen_pages = 0

                    time.sleep(self.request_delay)
                    page += 1

                except Exception as e:
                    print(f"Error scraping page {page} for keyword '{label}': {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("Too many errors for this keyword. Moving on.")
                        break
                    time.sleep(self.request_delay)
                    continue

        return list(dict.fromkeys(all_job_urls))

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

            # Extract all fields
            title_elem = soup.select_one('h1.margin-bottom-8.font-20.inline-middle.font-weight-500')
            title = title_elem.get_text().strip() if title_elem else None

            company_elem = soup.select_one('a[href^="/en/company/"]')
            company_name = company_elem.get_text().strip() if company_elem else None
            company_url = f"{self.base_url}{company_elem.get('href')}" if company_elem else None

            if company_url:
                self.database.companies.track_company_discovery(
                    company_url, self.source_site, self.session_id
                )

            location_elem = soup.select_one('span.color-gray')
            location = location_elem.get_text().strip() if location_elem else None

            desc_elem = soup.select_one('p.description.margin-top-12.margin-bottom-8.pre-wrap.text-start')
            description = desc_elem.get_text().strip() if desc_elem else None

            employment_elem = soup.select_one('div.margin-y-8 ul li.description')
            employment_type = employment_elem.get_text().strip().lower().replace(' ', '_') if employment_elem else 'unknown'

            external_id = job_url.split('/')[-1] if '/' in job_url else None

            seniority_elem = soup.select_one('div.margin-y-8 p:contains("Seniority") + ul li a')
            experience_level = seniority_elem.get_text().strip().lower().replace(' ', '_') if seniority_elem else 'unknown'

            posted_elem = soup.select_one('p.text-sm.margin-right-16')
            posted_date_raw = posted_elem.get_text().strip() if posted_elem else None

            # Extract gender requirement
            gender_requirement = 'unknown'
            title_text = (title or '').lower()
            description_text = (description or '').lower()

            if '(female)' in title_text or (title and 'Ø®Ø§Ù†Ù…' in title) or 'female' in description_text:
                gender_requirement = 'female'
            elif '(male)' in title_text or (title and 'Ø¢Ù‚Ø§' in title) or 'male' in description_text:
                gender_requirement = 'male'

            # Create JobPosting model with validation
            today = date.today()
            
            job_posting = JobPosting(
                raw_scrape_id=scrape_id,
                external_id=external_id,
                source_site=self.source_site,
                source_url=job_url,
                title_persian=title or "",  # Required field, provide empty string if None
                description_persian=description,
                company_name_raw=company_name,
                company_url=company_url,
                location_raw=location,
                employment_type=employment_type,
                experience_level=experience_level,
                gender_requirement=gender_requirement,
                processing_status='pending',
                first_seen_date=today,
                last_seen_date=today
            )

            print(f"âœ… Created JobPosting model for: {title}")
            return job_posting

        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return None








