# src/scrapers/jobinja/scraper.py
from __future__ import annotations
from typing import List
from src.scrapers.base.base_scraper import BaseScraper
from src.database.models import JobPosting
from datetime import date
import time
import random
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class JobinjaScraper(BaseScraper):

    def __init__(self, database, session_id: str, rate_limiter_registry=None):
        # Force Selenium for Arvan CDN bypass
        super().__init__(
            database,
            session_id,
            method="selenium",
            rate_limiter_registry=rate_limiter_registry
        )

        self.base_url = "https://jobinja.ir"
        self.jobs_list_url = "https://jobinja.ir/jobs"
        
        # Anti-detection settings
        self.request_delay_min = 3
        self.request_delay_max = 7
        self.page_delay_min = 5
        self.page_delay_max = 10
    
    def get_source_site(self) -> str:
        return "jobinja"
    
    def _random_delay(self, min_seconds: float, max_seconds: float):
        """Random delay to appear more human"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def _scroll_page(self):
        """Simulate human scrolling behavior"""
        if not self.driver:
            return
            
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            current_position = 0
            scroll_increment = random.randint(300, 500)
            
            while current_position < total_height:
                current_position += scroll_increment
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(random.uniform(0.1, 0.3))
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1.0))
        except:
            pass
    
    def _wait_for_page_load(self):
        """Wait for Arvan CDN challenge to complete and job cards to load"""
        try:
            if not self.wait or not self.driver:
                return
                
            print("⏳ Waiting for Arvan CDN challenge...")
            time.sleep(5)
            
            # Wait up to 30 seconds for challenge to complete
            challenge_timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < challenge_timeout:
                try:
                    # Check if challenge page is still visible
                    challenge_elements = self.driver.find_elements(By.CLASS_NAME, "error-section")
                    if not challenge_elements or not any(elem.is_displayed() for elem in challenge_elements):
                        print("✓ Challenge passed!")
                        break
                except:
                    break
                
                time.sleep(1)
                print(".", end="", flush=True)
            
            # Check for reCAPTCHA and click it if present
            try:
                print("\n🔍 Checking for reCAPTCHA...")
                recaptcha_frame = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                if recaptcha_frame:
                    print("⚠️ reCAPTCHA detected - attempting to click...")
                    self.driver.switch_to.frame(recaptcha_frame[0])
                    
                    # Click the checkbox
                    checkbox = self.wait.until(EC.element_to_be_clickable(
                        (By.CLASS_NAME, "recaptcha-checkbox-border")
                    ))
                    checkbox.click()
                    print("✓ Clicked reCAPTCHA checkbox")
                    
                    # Switch back to main content
                    self.driver.switch_to.default_content()
                    time.sleep(3)
            except Exception as e:
                print(f"ℹ️ No reCAPTCHA or already solved: {e}")
                self.driver.switch_to.default_content()
            
            # Now wait for actual job listings
            print("⏳ Waiting for job listings...")
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a.c-jobListView__titleLink")
            ))
            print("✓ Job listings loaded")
            
            time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            print(f"\n⚠️ Page load issue: {e}")
    
    def discover_job_urls(self) -> List[str]:
        """Paginate through job search pages and collect job URLs"""
        all_job_urls = []
        last_success_page = self.database.scrapes.get_last_success_page(self.source_site)
        page = max(1, last_success_page + 1)
        consecutive_errors = 0
        max_consecutive_errors = 3
        consecutive_seen_pages = 0
        max_consecutive_seen_pages = 5
        seen_ratio_threshold = 1.0

        while True:
            page_url = f"{self.jobs_list_url}?page={page}"
            print(f"\n{'='*60}")
            print(f"📄 Scraping page {page}: {page_url}")
            print(f"{'='*60}")

            try:
                html, status_code = self.get_page_content(page_url)
                
                # Check if we got challenge page instead of content
                if self._is_challenge_page(html):
                    print(f"⚠️ Still on challenge page after timeout")
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"❌ Too many challenge failures. Stopping.")
                        break
                    
                    print(f"💤 Taking extended break (60-120 seconds)...")
                    time.sleep(random.uniform(60, 120))
                    continue
                
                # Simulate human behavior
                self._scroll_page()
                
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
                    print(f"✓ No more results found at page {page}")
                    break

                # Parse job URLs
                page_job_urls = self._extract_job_urls_from_page(html)
                
                if len(page_job_urls) == 0:
                    print(f"⚠️ No jobs found on page {page}")
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"❌ No jobs for {max_consecutive_errors} consecutive pages. Stopping.")
                        break
                    
                    time.sleep(random.uniform(30, 60))
                    continue
                
                consecutive_errors = 0
                all_job_urls.extend(page_job_urls)
                print(f"✓ Found {len(page_job_urls)} jobs | Total: {len(all_job_urls)}")

                seen_count, total_count, seen_ratio = self._seen_ratio_on_page(page_job_urls)
                if total_count > 0 and seen_ratio >= seen_ratio_threshold:
                    consecutive_seen_pages += 1
                    print(f"Seen-only page streak: {consecutive_seen_pages}/{max_consecutive_seen_pages}")
                    if consecutive_seen_pages >= max_consecutive_seen_pages:
                        print("Too many consecutive seen-only pages. Stopping.")
                        break
                else:
                    consecutive_seen_pages = 0

                # Update progress after a successful page
                self.database.scrapes.update_last_success_page(
                    self.source_site, page, self.session_id
                )
                
                # Longer delay between pages
                delay = random.uniform(self.page_delay_min, self.page_delay_max)
                print(f"💤 Waiting {delay:.1f} seconds before next page...")
                time.sleep(delay)
                page += 1

            except Exception as e:
                print(f"❌ Error scraping page {page}: {e}")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"❌ Too many errors. Stopping.")
                    break
                
                time.sleep(random.uniform(30, 60))

        return all_job_urls
    
    def _is_challenge_page(self, html: str) -> bool:
        """Check if we're stuck on Arvan CDN challenge page"""
        challenge_indicators = [
            "error-section__subtitle--waiting",
            "Checking your browser before accessing",
            "در حال بررسی مرورگر پیش از اتصال به سایت"
        ]
        return any(indicator in html for indicator in challenge_indicators)
    
    def _is_no_results_page(self, html: str) -> bool:
        """Check if page shows 'no jobs found' message"""
        return "متاسفانه‌ برای فیلتر‌های اعمال شده نتیجه‌ای یافت نشد" in html
    
    def _extract_job_urls_from_page(self, html: str) -> List[str]:
        """Extract job URLs from job listing page HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        job_urls = []
        
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
    
    def scrape_job_detail(self, job_url: str) -> JobPosting | None:
        """Scrape individual job detail page and return JobPosting model"""
        try:
            # Random delay
            self._random_delay(self.request_delay_min, self.request_delay_max)
            
            html, status_code = self.get_page_content(job_url)
            print(f"📋 Scraping: {job_url}")
            
            # Check for challenge page
            if self._is_challenge_page(html):
                print(f"⚠️ Challenge page on job detail, taking break...")
                time.sleep(random.uniform(30, 60))
                return None
            
            self._scroll_page()
            
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
            title_elem = soup.select_one('div.c-jobView__titleText h1')
            title = title_elem.get_text().strip() if title_elem else None

            company_elem = soup.select_one('h2.c-companyHeader__name')
            company_name = company_elem.get_text().strip() if company_elem else None

            company_url_elem = soup.select_one('a.c-companyHeader__logoLink[href]')
            company_url = str(company_url_elem.get('href')) if company_url_elem and company_url_elem.get('href') else None

            if company_url:
                self.database.companies.track_company_discovery(
                    company_url, self.source_site, self.session_id
                )
            
            location_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Location")) .tags span.black')
            location = location_elem.get_text().strip() if location_elem else None
            
            desc_elem = soup.select_one('h4:contains("Job description") + div.o-box__text')
            description = desc_elem.get_text().strip() if desc_elem else None
            
            employment_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Type of cooperation")) .tags span.black')
            employment_type = employment_elem.get_text().strip().lower().replace(' ', '_') if employment_elem else 'unknown'
            
            experience_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Minimum work experience")) .tags span.black')
            experience_level = experience_elem.get_text().strip().lower().replace(' ', '_') if experience_elem else 'unknown'
            
            education_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Minimum educational qualification")) .tags span.black')
            if education_elem:
                education_text = education_elem.get_text().strip()
                education_level = 'none' if education_text == 'مهم‌ نیست' else education_text
            else:
                education_level = 'unknown'

            skills_elems = soup.select('li.c-infoBox__item:has(h4:contains("Required skills")) .tags span.black')
            skills_required = [skill.get_text().strip() for skill in skills_elems] if skills_elems else None
            
            salary_elem = soup.select_one('li.c-infoBox__item:has(h4:contains("Rights")) .tags span.black')
            salary_raw = salary_elem.get_text().strip() if salary_elem else None
            
            external_id = job_url.split('/')[-1] if '/' in job_url else None

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
                employment_type=employment_type,
                experience_level=experience_level,
                gender_requirement=gender_requirement,
                education_level=education_level,
                skills_required=skills_required,
                processing_status='pending',
                first_seen_date=today,
                last_seen_date=today
            )
            
            print(f"  ✓ Created JobPosting model for: {title}")
            return job_posting
            
        except Exception as e:
            print(f"❌ Error scraping {job_url}: {e}")
            return None
