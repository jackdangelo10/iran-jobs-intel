# src/config/settings.py
"""
Application settings and configuration.
Loads from environment variables (local) or GCP Secret Manager (cloud).
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass

@dataclass
class Settings:
    """Application configuration settings."""
    
    # Environment
    environment: str  # 'development' or 'production'
    is_cloud_run: bool
    gcp_project_id: str | None
    
    # Database
    database_url: str
    
    # Scraping configuration
    request_delay_seconds: int = 2
    max_retries: int = 3
    scraping_timeout_seconds: int = 30

    # Discovery resume/stop controls
    max_consecutive_seen_pages: int = 5
    seen_ratio_threshold: float = 1.0
    resume_page_offset: int = -1
    force_full_crawl: bool = False
    
    # Selenium configuration
    headless: bool = True
    page_load_timeout: int = 90

def load_settings() -> Settings:
    """
    Load application settings with environment auto-detection.
    
    Environment Detection:
    - Cloud Run: K_SERVICE environment variable is set
    - Local: K_SERVICE is not set
    
    Configuration Loading Priority:
    1. Cloud Run: GCP Secret Manager
    2. Local: .env file
    3. Fallback: Environment variables
    
    Returns:
        Settings: Loaded configuration
        
    Raises:
        ValueError: If required settings are missing
    """

    # Avoid Windows cp1252 encoding crashes when printing Unicode.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Detect environment
    # K_SERVICE is set by Cloud Run Services; CLOUD_RUN_JOB is set by Cloud Run Jobs
    is_cloud_run = (os.getenv('K_SERVICE') is not None
                    or os.getenv('CLOUD_RUN_JOB') is not None)
    environment = 'production' if is_cloud_run else 'development'

    print(f"🔧 Environment: {environment}")
    print(f"☁️  Cloud Run: {is_cloud_run}")

    gcp_project_id = os.getenv('GCP_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')

    # Load database URL
    database_url = _load_database_url(is_cloud_run, gcp_project_id)

    # Load optional overrides from environment
    request_delay = int(os.getenv('SCRAPER_DELAY_SECONDS', '2'))
    max_retries = int(os.getenv('SCRAPER_MAX_RETRIES', '3'))
    headless = os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true'
    page_load_timeout = int(os.getenv('SELENIUM_PAGE_LOAD_TIMEOUT', '90'))
    max_consecutive_seen_pages = int(os.getenv('SCRAPER_MAX_CONSECUTIVE_SEEN_PAGES', '5'))
    seen_ratio_threshold = float(os.getenv('SCRAPER_SEEN_RATIO_THRESHOLD', '1.0'))
    resume_page_offset = int(os.getenv('SCRAPER_RESUME_PAGE_OFFSET', '-1'))
    force_full_crawl = os.getenv('SCRAPER_FORCE_FULL_CRAWL', 'false').lower() == 'true'

    return Settings(
        environment=environment,
        is_cloud_run=is_cloud_run,
        gcp_project_id=gcp_project_id,
        database_url=database_url,
        request_delay_seconds=request_delay,
        max_retries=max_retries,
        headless=headless,
        page_load_timeout=page_load_timeout,
        max_consecutive_seen_pages=max_consecutive_seen_pages,
        seen_ratio_threshold=seen_ratio_threshold,
        resume_page_offset=resume_page_offset,
        force_full_crawl=force_full_crawl
    )


def _load_database_url(is_cloud_run: bool, gcp_project_id: str | None) -> str:
    """
    Load database URL based on environment.
    
    Args:
        is_cloud_run: Whether running in Cloud Run
        gcp_project_id: GCP project ID (required for Cloud Run)
        
    Returns:
        Database connection URL
        
    Raises:
        ValueError: If database URL cannot be loaded
    """
    if os.getenv("IRAN_JOBS_DRY_RUN") == "1":
        print("🧪 Dry run mode: skipping database URL resolution")
        return "postgresql://dry-run/dry-run"

    if is_cloud_run:
        # Cloud Run: Must use Secret Manager
        print("📡 Loading DATABASE_URL from GCP Secret Manager...")
        
        if not gcp_project_id:
            raise ValueError(
                "GCP_PROJECT or GOOGLE_CLOUD_PROJECT environment variable must be set in Cloud Run"
            )
        
        from src.utils.secrets import get_secret
        
        try:
            database_url = get_secret("IRAN_JOBS_SCRAPER_DATABASE_URL", project_id=gcp_project_id)
            if isinstance(database_url, str):
                database_url = database_url.strip()
            print("✅ Database URL loaded from Secret Manager")
            return database_url
        except Exception as e:
            raise ValueError(f"Failed to load database URL from Secret Manager: {e}")
    
    else:
        # Local development: Try .env file first
        print("📁 Loading DATABASE_URL from .env file...")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        database_url = os.getenv('IRAN_JOBS_SCRAPER_DATABASE_URL')
        if isinstance(database_url, str):
            database_url = database_url.strip()
        
        if not database_url:
            raise ValueError(
                "IRAN_JOBS_SCRAPER_DATABASE_URL not found in .env file. "
                "Create a .env file with: IRAN_JOBS_SCRAPER_DATABASE_URL=postgresql://..."
            )
        
        print("✅ Database URL loaded from .env")
        return database_url


# Global settings instance - loaded once on import
settings = load_settings()

