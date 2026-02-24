#!/usr/bin/env python3
"""
Test runner for Jobinja scraper.
Outputs all scraped data to data/jobinja/ directory.

Usage:
    python tests/test_scrapers/run_jobinja.py
    python tests/test_scrapers/run_jobinja.py --pages 3 --jobs 10
    
Output:
    data/jobinja/
    ├── session_<uuid>.json
    ├── discovered_urls.json
    ├── raw_html/
    └── scraped_jobs/
"""
from __future__ import annotations
import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database import IranJobsDB
from src.scrapers.jobinja.scraper import JobinjaScraper


def setup_output_directory(base_path: Path) -> dict[str, Path]:
    """Create output directory structure."""
    base_path.mkdir(parents=True, exist_ok=True)
    
    paths = {
        'base': base_path,
        'raw_html': base_path / 'raw_html',
        'scraped_jobs': base_path / 'scraped_jobs',
    }
    
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    
    return paths


def save_json(data: Any, filepath: Path) -> None:
    """Save data as JSON with pretty formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  ✓ Saved: {filepath}")


def run_jobinja_test(limit_pages: int | None = None, limit_jobs: int | None = None) -> dict[str, Any]:
    """
    Run Jobinja scraper and save all output.
    
    Args:
        limit_pages: Limit number of listing pages to scrape (None = all)
        limit_jobs: Limit number of job details to scrape (None = all)
        
    Returns:
        Dict with test results
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    print("=" * 80)
    print("🇮🇷 Jobinja Scraper Test Run")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"Start Time: {start_time.isoformat()}")
    if limit_pages:
        print(f"Page Limit: {limit_pages}")
    if limit_jobs:
        print(f"Job Limit: {limit_jobs}")
    print("⚠️  Note: Jobinja has Arvan CDN protection - may be slower")
    print("=" * 80)
    print()
    
    # Setup output directory
    output_base = Path('data/jobinja')
    paths = setup_output_directory(output_base)
    
    # Initialize database
    print("🔌 Connecting to database...")
    db = IranJobsDB()
    print("✅ Database connected")
    print()
    
    # Create scraper
    print("🔧 Initializing Jobinja scraper...")
    scraper = JobinjaScraper(db, session_id)
    print("✅ Scraper initialized")
    print()
    
    try:
        # Phase 1: Discover URLs
        print("=" * 80)
        print("📡 Phase 1: Discovering Job URLs")
        print("=" * 80)
        
        discovered_urls = []
        page = 1
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while True:
            if limit_pages and page > limit_pages:
                print(f"⏹️  Reached page limit ({limit_pages})")
                break
            
            page_url = f"{scraper.jobs_list_url}?page={page}"
            print(f"📄 Page {page}: {page_url}")
            
            try:
                html, status_code = scraper.get_page_content(page_url)
                
                # Check for challenge page
                if scraper._is_challenge_page(html):
                    print(f"  ⚠️  Arvan CDN challenge detected, waiting...")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"  ❌ Too many challenges, stopping")
                        break
                    continue
                
                consecutive_errors = 0
                
                # Save raw HTML
                html_file = paths['raw_html'] / f'listing_page_{page}.html'
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"  ✓ Saved HTML ({len(html)} bytes)")
                
                # Check for end of results
                if scraper._is_no_results_page(html):
                    print(f"  ℹ️  No more results")
                    break
                
                # Extract URLs
                page_urls = scraper._extract_job_urls_from_page(html)
                
                if len(page_urls) == 0:
                    print(f"  ⚠️  No jobs found on page")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"  ❌ No jobs for {max_consecutive_errors} consecutive pages")
                        break
                    continue
                
                discovered_urls.extend(page_urls)
                print(f"  ✓ Found {len(page_urls)} jobs (Total: {len(discovered_urls)})")
                
                page += 1
                
            except Exception as e:
                print(f"  ❌ Error on page {page}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
        
        # Save discovered URLs
        print()
        print(f"✅ Discovery complete: {len(discovered_urls)} jobs found")
        
        urls_data = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'total_urls': len(discovered_urls),
            'unique_urls': len(set(discovered_urls)),
            'urls': discovered_urls
        }
        save_json(urls_data, paths['base'] / 'discovered_urls.json')
        print()
        
        # Phase 2: Scrape Job Details
        print("=" * 80)
        print("🔍 Phase 2: Scraping Job Details")
        print("=" * 80)
        
        unique_urls = list(dict.fromkeys(discovered_urls))
        jobs_to_scrape = unique_urls[:limit_jobs] if limit_jobs else unique_urls
        
        print(f"Jobs to scrape: {len(jobs_to_scrape)}")
        print()
        
        scraped_jobs = []
        failed_jobs = []
        
        for idx, job_url in enumerate(jobs_to_scrape, 1):
            print(f"[{idx}/{len(jobs_to_scrape)}] {job_url}")
            
            try:
                job_posting = scraper.scrape_job_detail(job_url)
                
                if job_posting:
                    job_dict = job_posting.model_dump(exclude_none=True)
                    
                    job_id = job_posting.external_id or f"job_{idx}"
                    job_file = paths['scraped_jobs'] / f'{job_id}.json'
                    save_json(job_dict, job_file)
                    
                    scraped_jobs.append(job_dict)
                    print(f"  ✓ Scraped: {job_posting.title_persian}")
                else:
                    print(f"  ⚠️  No data returned")
                    failed_jobs.append({'url': job_url, 'reason': 'no_data'})
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                failed_jobs.append({'url': job_url, 'reason': str(e)})
        
        print()
        print(f"✅ Scraping complete: {len(scraped_jobs)} jobs scraped, {len(failed_jobs)} failed")
        print()
        
        # Save consolidated results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        session_data = {
            'session_id': session_id,
            'scraper': 'jobinja',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'phase_1_discovery': {
                'total_discovered': len(discovered_urls),
                'unique_discovered': len(unique_urls),
                'pages_scraped': page - 1
            },
            'phase_2_detail_scraping': {
                'total_attempted': len(jobs_to_scrape),
                'successful': len(scraped_jobs),
                'failed': len(failed_jobs),
                'success_rate': (len(scraped_jobs) / len(jobs_to_scrape) * 100) if jobs_to_scrape else 0
            },
            'limits': {
                'limit_pages': limit_pages,
                'limit_jobs': limit_jobs
            }
        }
        
        save_json(session_data, paths['base'] / f'session_{session_id}.json')
        save_json(scraped_jobs, paths['base'] / 'all_jobs.json')
        
        if failed_jobs:
            save_json(failed_jobs, paths['base'] / 'failed_jobs.json')
        
        # Print summary
        print("=" * 80)
        print("📊 Test Summary")
        print("=" * 80)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Discovered: {len(discovered_urls)} URLs")
        print(f"Scraped: {len(scraped_jobs)} jobs")
        print(f"Failed: {len(failed_jobs)} jobs")
        print(f"Success Rate: {session_data['phase_2_detail_scraping']['success_rate']:.1f}%")
        print()
        print(f"📁 Output Directory: {paths['base'].absolute()}")
        print("=" * 80)
        
        return session_data
        
    finally:
        scraper.cleanup()
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Jobinja scraper and save results')
    parser.add_argument('--pages', type=int, help='Limit number of listing pages (default: all)')
    parser.add_argument('--jobs', type=int, help='Limit number of jobs to scrape (default: all)')
    
    args = parser.parse_args()
    
    try:
        results = run_jobinja_test(
            limit_pages=args.pages,
            limit_jobs=args.jobs
        )
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)