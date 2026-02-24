# src/runners/processor_job.py
"""
Cloud Run Job entry point for processing scraped data.

This job:
1. Translates Persian -> English (with translation cache)
2. Normalizes company/location entities
3. Extracts and links skills
4. Updates job_postings processing status and quality fields
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from src.database import IranJobsDB
from src.processors import JobProcessor


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


def run_processor_job(dry_run: bool = False) -> dict[str, Any]:
    """
    Run the processing pipeline for pending job postings.

    Args:
        dry_run: If True, inspect pending workload without writing data.

    Returns:
        Structured result summary.
    """
    logger.info("🔄 Processor job starting...")

    batch_size = int(os.getenv("PROCESSOR_BATCH_SIZE", "200"))
    db = None

    try:
        if dry_run:
            logger.info("🧪 Dry run enabled - skipping database work")
            return {
                "status": "dry_run",
                "batch_size": batch_size,
                "pipeline": [
                    "translation_cache",
                    "company_normalization",
                    "location_normalization",
                    "skill_extraction",
                    "job_postings_update",
                ],
            }

        logger.info("🔌 Connecting to database...")
        db = IranJobsDB()
        logger.info("✅ Database connected")

        processor = JobProcessor(db)
        result = processor.run(batch_size=batch_size, dry_run=dry_run)

        logger.info("✅ Processor job finished")
        logger.info("📊 Processor results: %s", result)
        return result
    finally:
        if db:
            logger.info("🔌 Closing database connection...")
            db.close()
            logger.info("✅ Database connection closed")


if __name__ == "__main__":
    try:
        dry_run = "--dry-run" in sys.argv[1:]
        run_processor_job(dry_run=dry_run)
        sys.exit(0)
    except KeyboardInterrupt:
        logger.warning("⚠️ Processor job interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Processor job failed: {e}", exc_info=True)
        sys.exit(1)
