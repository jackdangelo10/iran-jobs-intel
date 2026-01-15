# src/runners/scraper_job.py
"""
Cloud Run Job entry point for scraping Iranian job sites.

This job:
1. Scrapes IranTalent, Jobinja, and JobVision
2. Discovers job URLs from listing pages
3. Scrapes detailed job information
4. Stores raw HTML and structured data in PostgreSQL

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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_scraper_job() -> dict[str, Any]:
    """
    Main scraping job orchestration.
    
    Scrapes all three Iranian job sites in sequence and stores
    raw data in the database for later processing.
    
    Returns:
        Dict with results from each scraper
        
    Raises:
        SystemExit: If job fails critically
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Iran Jobs Scraper Job")
    logger.info(f"📅 Start Time: {start_time.isoformat()}")
    logger.info(f"🆔 Session ID: {session_id}")
    logger.info(f"🌍 Environment: {settings.environment}")
    logger.info("=" * 80)
    
    db = None
    results: dict[str, Any] = {}
    
    try:
        # Initialize database connection
        logger.info("🔌 Connecting to database...")
        db = IranJobsDB()
        logger.info("✅ Database connected")
        
        # Define scrapers to run
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
        
        # Run each scraper
        for scraper_config in scrapers_config:
            if not scraper_config['enabled']:
                logger.info(f"⏭️  Skipping {scraper_config['name']} (disabled)")
                continue
            
            site_name = scraper_config['name']
            
            try:
                logger.info("-" * 80)
                logger.info(f"🔍 Starting {site_name} scraper...")
                logger.info("-" * 80)
                
                # Initialize scraper
                scraper = scraper_config['class'](db, session_id)
                
                # Run scraping session
                result = scraper.run_scraping_session()
                
                # Store results
                results[site_name] = {
                    'status': 'success',
                    'discovered': result.get('discovered', 0),
                    'scraped': result.get('scraped', 0),
                    'failed': result.get('failed', 0)
                }
                
                logger.info(f"✅ {site_name} complete:")
                logger.info(f"   - Discovered: {result.get('discovered', 0)} jobs")
                logger.info(f"   - Scraped: {result.get('scraped', 0)} jobs")
                logger.info(f"   - Failed: {result.get('failed', 0)} jobs")
                
            except Exception as e:
                logger.error(f"❌ {site_name} failed: {e}", exc_info=True)
                results[site_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                # Continue with other scrapers even if one fails
        
        # Calculate totals
        total_discovered = sum(
            r.get('discovered', 0) for r in results.values() if r.get('status') == 'success'
        )
        total_scraped = sum(
            r.get('scraped', 0) for r in results.values() if r.get('status') == 'success'
        )
        total_failed = sum(
            r.get('failed', 0) for r in results.values() if r.get('status') == 'success'
        )
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("🎉 Scraper Job Complete")
        logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        logger.info(f"📊 Total Discovered: {total_discovered}")
        logger.info(f"✅ Total Scraped: {total_scraped}")
        logger.info(f"❌ Total Failed: {total_failed}")
        logger.info("=" * 80)
        
        # Check if any scrapers succeeded
        success_count = sum(1 for r in results.values() if r.get('status') == 'success')
        
        if success_count == 0:
            logger.error("❌ All scrapers failed!")
            sys.exit(1)
        
        return results
        
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