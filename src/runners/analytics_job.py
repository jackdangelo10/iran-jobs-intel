# src/runners/analytics_job.py
"""
Cloud Run Job entry point for computing analytics and maintaining data freshness.

This job runs after every scraper + processor cycle and:
1. Deactivates job postings no longer seen on job boards (stale > 14 days)
2. Updates company hiring metrics (active_job_postings, hiring_velocity_30d)
3. Logs a daily summary snapshot to processing_logs
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from src.database import IranJobsDB
from src.analytics import AnalyticsEngine


def _ensure_utf8_console() -> None:
    """Avoid Windows cp1252 encoding crashes when logs contain Unicode."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_ensure_utf8_console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_analytics_job() -> dict[str, Any]:
    """
    Run the full analytics pipeline.

    Returns:
        Structured result summary.
    """
    logger.info("📊 Analytics job starting...")

    stale_days = int(os.getenv("ANALYTICS_STALE_DAYS", "14"))
    db = None

    try:
        logger.info("🔌 Connecting to database...")
        db = IranJobsDB()
        logger.info("✅ Database connected")

        engine = AnalyticsEngine(db, stale_days=stale_days)
        result = engine.run()

        logger.info("✅ Analytics job finished")
        logger.info("📊 Results: %s", result)
        return result

    finally:
        if db:
            logger.info("🔌 Closing database connection...")
            db.close()
            logger.info("✅ Database connection closed")


if __name__ == "__main__":
    try:
        run_analytics_job()
        sys.exit(0)
    except KeyboardInterrupt:
        logger.warning("⚠️ Analytics job interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("💥 Analytics job failed: %s", e, exc_info=True)
        sys.exit(1)
