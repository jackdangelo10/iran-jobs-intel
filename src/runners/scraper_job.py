# src/runners/scraper_job.py
"""
Cloud Run Job entry point for scraping Iranian job sites.

REFACTORED FOR PARALLEL SCRAPING:
- Phase 1: Sequential discovery (find all job URLs)
- Phase 2: Parallel detail scraping (6 workers scrape simultaneously)

This job:
1. Scrapes IranTalent, Jobinja, and JobVision sequentially to discover URLs
2. Distributes discovered jobs to worker pool for parallel scraping
3. Stores raw HTML and structured data in PostgreSQL

Scheduled to run nightly via Cloud Scheduler.
"""
from __future__ import annotations
import sys
import logging
import uuid
from datetime import datetime
from typing import Any
from src.config.settings import settings
from src.database import IranJobsDB
from src.scrapers.irantalent.scraper import IranTalentScraper
from src.scrapers.jobinja.scraper import JobinjaScraper
from src.scrapers.jobvision.scraper import JobVisionScraper
from src.parallel import WorkerPool


def _ensure_utf8_console() -> None:
    """Avoid Windows cp1252 encoding crashes when logs contain Unicode."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_ensure_utf8_console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_scraper_job(dry_run: bool = False) -> dict[str, Any]:
    """
    Main scraping job orchestration with parallel execution.
    
    Two-phase approach:
    1. Discovery: Sequentially discover all job URLs from each site
    2. Parallel: Use worker pool to scrape job details in parallel
    
    Returns:
        Dict with results from each phase
        
    Raises:
        SystemExit: If job fails critically
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Iran Jobs Scraper Job (PARALLEL MODE)")
    logger.info(f"📅 Start Time: {start_time.isoformat()}")
    logger.info(f"🆔 Session ID: {session_id}")
    logger.info(f"🌍 Environment: {settings.environment}")
    logger.info("=" * 80)
    
    db = None

    # Static job config used by both dry-run and full-run paths.
    scrapers_config = [
        {
            'name': 'IranTalent',
            'class': IranTalentScraper,
            'enabled': True
        },
        {
            'name': 'Jobinja',
            'class': JobinjaScraper,
            'enabled': True
        },
        {
            'name': 'JobVision',
            'class': JobVisionScraper,
            'enabled': True
        }
    ]
    rate_limits = {
        'irantalent': 20,
        'jobinja': 15,
        'jobvision': 20
    }
    scraper_classes = {
        'IranTalentScraper': IranTalentScraper,
        'JobinjaScraper': JobinjaScraper,
        'JobVisionScraper': JobVisionScraper
    }

    try:
        if dry_run:
            logger.info("🧪 Dry run enabled - skipping database and network calls")
            return {
                'status': 'dry_run',
                'environment': settings.environment,
                'session_id': session_id,
                'validated': {
                    'enabled_scrapers': [
                        s['name'] for s in scrapers_config if s['enabled']
                    ],
                    'rate_limits': rate_limits,
                    'worker_count': 6,
                    'scraper_classes': list(scraper_classes.keys())
                }
            }

        # Initialize database connection
        logger.info("🔌 Connecting to database...")
        db = IranJobsDB()
        logger.info("✅ Database connected")
        
        # ====================================================================
        # PHASE 1: DISCOVERY (Sequential) - ~6 minutes
        # ====================================================================
        logger.info("")
        logger.info("=" * 80)
        logger.info("📡 PHASE 1: DISCOVERING JOB URLS (Sequential)")
        logger.info("=" * 80)
        
        discovery_start = datetime.now()
        
        # Track discovered jobs for parallel phase
        all_discovered_jobs = []
        discovery_results = {}
        
        # Run discovery for each site sequentially
        for scraper_config in scrapers_config:
            if not scraper_config['enabled']:
                logger.info(f"⏭️  Skipping {scraper_config['name']} (disabled)")
                continue
            
            site_name = scraper_config['name']
            scraper_class = scraper_config['class']
            
            try:
                logger.info("-" * 80)
                logger.info(f"🔍 Discovering URLs from {site_name}...")
                logger.info("-" * 80)
                
                # Create scraper (no rate limiter for discovery)
                scraper = scraper_class(db, session_id)
                
                try:
                    # Discover job URLs (paginate through search results)
                    job_urls = scraper.discover_job_urls()
                    
                    # Remove duplicates
                    unique_urls = list(dict.fromkeys(job_urls))
                    
                    logger.info(f"✅ {site_name}: Discovered {len(unique_urls)} unique jobs")
                    
                    # Record discoveries and tracking in batches
                    db.jobs.record_job_discoveries_batch(
                        session_id, scraper.source_site, unique_urls
                    )
                    db.jobs.update_job_tracking_batch(
                        unique_urls, scraper.source_site, session_id
                    )

                    for job_url in unique_urls:
                        # Add to parallel queue
                        all_discovered_jobs.append({
                            'job_url': job_url,
                            'source_site': scraper.source_site,
                            'scraper_class_name': scraper_class.__name__
                        })
                    
                    discovery_results[site_name] = {
                        'status': 'success',
                        'discovered': len(unique_urls)
                    }
                    
                finally:
                    # Cleanup scraper
                    scraper.cleanup()
                
            except Exception as e:
                logger.error(f"❌ {site_name} discovery failed: {e}", exc_info=True)
                discovery_results[site_name] = {
                    'status': 'error',
                    'error': str(e),
                    'discovered': 0
                }
        
        discovery_duration = (datetime.now() - discovery_start).total_seconds()
        total_discovered = sum(
            r.get('discovered', 0) for r in discovery_results.values()
        )
        
        logger.info("=" * 80)
        logger.info(f"✅ Phase 1 Complete: Discovery")
        logger.info(f"   Duration: {discovery_duration:.1f} seconds")
        logger.info(f"   Total discovered: {total_discovered} jobs")
        logger.info("=" * 80)
        
        if total_discovered == 0:
            logger.warning("⚠️  No jobs discovered - skipping parallel phase")
            return {
                'phase_1_discovery': discovery_results,
                'phase_2_parallel': {'status': 'skipped'},
                'total_discovered': 0,
                'total_scraped': 0
            }
        
        # ====================================================================
        # PHASE 2: PARALLEL DETAIL SCRAPING - ~13 minutes
        # ====================================================================
        logger.info("")
        logger.info("=" * 80)
        logger.info("🚀 PHASE 2: PARALLEL DETAIL SCRAPING")
        logger.info("=" * 80)
        
        parallel_start = datetime.now()
        
        # Get jobs needing scraping
        unscraped_jobs = db.jobs.get_jobs_needing_scraping(limit=10000)
        
        logger.info(f"📋 Jobs to scrape: {len(unscraped_jobs)}")
        
        if len(unscraped_jobs) == 0:
            logger.info("✅ No jobs need scraping - all up to date")
            parallel_results = {'status': 'skipped', 'reason': 'no_jobs_needed'}
        else:
            # Create worker pool
            pool = WorkerPool(
                database_conninfo=settings.database_url,
                session_id=session_id,
                num_workers=6,  # Tune based on Cloud Run resources
                rate_limits=rate_limits,
                scraper_classes=scraper_classes
            )
            
            # Convert database results to job queue format
            jobs_for_pool = [
                {
                    'job_url': job['job_url'],
                    'source_site': job['source_site'],
                    'scraper_class_name': {
                        'irantalent': 'IranTalentScraper',
                        'jobinja': 'JobinjaScraper',
                        'jobvision': 'JobVisionScraper'
                    }[job['source_site']]
                }
                for job in unscraped_jobs
            ]
            
            # Add jobs to pool
            pool.add_jobs(jobs_for_pool)
            
            # Run parallel scraping
            parallel_results = pool.run()
        
        parallel_duration = (datetime.now() - parallel_start).total_seconds()
        
        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎉 SCRAPER JOB COMPLETE")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Duration: {total_duration:.1f} seconds")
        logger.info(f"   - Phase 1 (Discovery): {discovery_duration:.1f}s")
        logger.info(f"   - Phase 2 (Parallel): {parallel_duration:.1f}s")
        logger.info("")
        logger.info(f"📊 Results:")
        logger.info(f"   - Total Discovered: {total_discovered}")
        if parallel_results.get('status') != 'skipped':
            logger.info(f"   - Total Scraped: {parallel_results.get('successful', 0)}")
            logger.info(f"   - Failed: {parallel_results.get('failed', 0)}")
            logger.info(f"   - Success Rate: {parallel_results.get('success_rate', 0):.1f}%")
        logger.info("=" * 80)
        
        return {
            'phase_1_discovery': discovery_results,
            'phase_2_parallel': parallel_results,
            'total_discovered': total_discovered,
            'total_scraped': parallel_results.get('successful', 0),
            'total_duration': total_duration
        }
        
    except Exception as e:
        logger.error(f"💥 Scraper job failed critically: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # Always close database connection
        if db:
            logger.info("🔌 Closing database connection...")
            db.close()
            logger.info("✅ Database connection closed")


if __name__ == "__main__":
    """
    Entry point when running as Cloud Run Job or locally.
    
    Usage:
        python -m src.runners.scraper_job
    """
    try:
        results = run_scraper_job()
        sys.exit(0)  # Success
    except KeyboardInterrupt:
        logger.info("⚠️  Job interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Job failed: {e}", exc_info=True)
        sys.exit(1)
