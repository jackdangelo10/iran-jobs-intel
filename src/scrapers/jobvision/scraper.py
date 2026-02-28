# src/scrapers/jobvision/scraper.py
from __future__ import annotations
from typing import List
from src.scrapers.base.base_scraper import BaseScraper
from src.config.settings import settings
from src.database.models import JobPosting
from datetime import date
import time
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

class JobVisionScraper(BaseScraper):

    def __init__(self, database, session_id: str, rate_limiter_registry=None):
        # Force Selenium for JobVision
        super().__init__(
            database,
            session_id,
            method="selenium",
            rate_limiter_registry=rate_limiter_registry
        )

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

    def _get_keywords(self) -> list[str]:
        if settings.water_focus_enabled:
            return settings.jobvision_water_keywords_fa or ["آب"]
        return [""]

    def _set_page(self, url: str, page: int) -> str:
        parsed = urlsplit(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["page"] = str(page)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    def _resolve_keyword_search_url(self, keyword: str) -> str:
        if not keyword:
            return self.jobs_list_url

        try:
            driver = self._get_or_create_driver()
            driver.get(self.jobs_list_url)
            self._wait_for_page_load()

            search_input = driver.find_element(By.CSS_SELECTOR, "input.keyword-input")
            search_input.clear()
            search_input.send_keys(keyword)
            search_input.send_keys(Keys.ENTER)
            time.sleep(2)

            current_url = driver.current_url
            if current_url:
                return current_url
        except Exception as e:
            print(f"Keyword URL resolution failed for '{keyword}': {e}")

        return f"{self.jobs_list_url}?{urlencode({'keyword': keyword})}"

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

            print(f"\nSearching JobVision keyword: {label}")

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
                        print(f"No jobs found on page {page} for keyword '{label}'")
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
                    print(f"Error fetching page {page} for keyword '{label}': {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("Too many errors for this keyword. Moving on.")
                        break
                    time.sleep(self.request_delay)
                    continue

        return list(dict.fromkeys(all_job_urls))

    def _is_no_results_page(self, html: str) -> bool:
        """Check if page shows 'no jobs found' message"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check if the empty state component is actually visible/active
        empty_state = soup.select_one('app-empty-state.ng-star-inserted')
        if empty_state:
            # Check if it has display content (not just ng-star-inserted)
            # The empty state is shown when there are actually no results
            return 'ÙØ±ØµØª Ø´ØºÙ„ÛŒ Ø¨Ø±Ø§ÛŒ Ø¬Ø³ØªØ¬ÙˆÛŒ Ø´Ù…Ø§ Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯' in empty_state.get_text()
        
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
            title_elem = soup.select_one('h1.text-black.font-size-1.font-weight-bold.py-2')
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
            location_elem = soup.select_one('span.text-muted.font-size-6')
            location = location_elem.get_text().strip() if location_elem else None
            
            # Extract job description
            desc_elem = soup.select_one('h2:contains("Job description and duties") + div')
            description = desc_elem.get_text().strip() if desc_elem else None
            
            # Extract gender requirement
            gender_elem = soup.select_one('div.requirement-value.text-black.bg-light')
            gender_requirement = 'not_specified'
            if gender_elem:
                gender_text = gender_elem.get_text().strip()
                if gender_text in ['There is no difference.', 'ØªÙØ§ÙˆØª Ù†Ø¯Ø§Ø±Ø¯', 'Ù…Ù‡Ù… Ù†ÛŒØ³Øª']:
                    gender_requirement = 'any'
                elif 'woman' in gender_text.lower() or 'female' in gender_text.lower() or 'Ø²Ù†' in gender_text or 'Ø®Ø§Ù†Ù…' in gender_text:
                    gender_requirement = 'female'
                elif 'man' in gender_text.lower() or 'male' in gender_text.lower() or 'Ù…Ø±Ø¯' in gender_text or 'Ø¢Ù‚Ø§' in gender_text:
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
            
            print(f"âœ… Created JobPosting model for: {title}")
            return job_posting
            
        except Exception as e:
            print(f"Error scraping job detail {job_url}: {e}")
            return None






