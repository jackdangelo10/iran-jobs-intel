#!/usr/bin/env python3
"""
Iran Jobs Intelligence Platform - Job Router

Entry point for all Cloud Run Jobs. Routes to the appropriate job runner
based on command-line argument.

Usage:
    python main.py scraper     # Run web scraping job
    python main.py processor   # Run data processing job
    python main.py analytics   # Run analytics computation job

Cloud Run Job Configuration:
    Each job type is deployed as a separate Cloud Run Job with different
    resource allocations and schedules, but they all use the same Docker image.
"""
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """
    Main entry point that routes to different job types.
    
    Reads the job type from sys.argv[1] and dispatches to the
    appropriate job runner module.
    """
    # Print startup banner
    logger.info("=" * 80)
    logger.info("🇮🇷 Iran Jobs Intelligence Platform")
    logger.info("=" * 80)
    
    # Validate command-line arguments
    if len(sys.argv) < 2:
        logger.error("❌ No job type specified!")
        logger.info("")
        logger.info("Usage: python main.py [scraper|processor|analytics]")
        logger.info("")
        logger.info("Available job types:")
        logger.info("  scraper     - Scrape Iranian job sites (IranTalent, Jobinja, JobVision)")
        logger.info("  processor   - Process raw data (translation, entity resolution)")
        logger.info("  analytics   - Compute metrics and generate insights")
        logger.info("")
        sys.exit(1)
    
    job_type = sys.argv[1].lower()
    logger.info(f"🚀 Job Type: {job_type.upper()}")
    logger.info("=" * 80)
    logger.info("")
    
    # Route to appropriate job runner
    try:
        if job_type == "scraper":
            logger.info("📡 Starting web scraping job...")
            from src.runners.scraper_job import run_scraper_job
            result = run_scraper_job()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Scraper job completed successfully")
            logger.info(f"📊 Results: {result}")
            logger.info("=" * 80)
            sys.exit(0)
            
        elif job_type == "processor":
            logger.info("🔄 Starting data processing job...")
            from src.runners.processor_job import run_processor_job
            result = run_processor_job()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Processor job completed successfully")
            logger.info(f"📊 Results: {result}")
            logger.info("=" * 80)
            sys.exit(0)
            
        elif job_type == "analytics":
            logger.info("📊 Starting analytics computation job...")
            from src.runners.analytics_job import run_analytics_job
            result = run_analytics_job()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Analytics job completed successfully")
            logger.info(f"📊 Results: {result}")
            logger.info("=" * 80)
            sys.exit(0)
            
        else:
            logger.error(f"❌ Unknown job type: '{job_type}'")
            logger.info("")
            logger.info("Valid job types: scraper, processor, analytics")
            logger.info("")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("⚠️  Job interrupted by user (Ctrl+C)")
        sys.exit(130)
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error(f"💥 Job failed with error: {e}")
        logger.error("=" * 80)
        logger.exception("Full error traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()