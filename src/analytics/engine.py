"""
Analytics Engine for Iran Jobs Intelligence Platform.

Runs after the scraper and processor to:
1. Deactivate job postings no longer visible on the job boards.
2. Refresh company hiring metrics (active postings, 30-day velocity).
3. Compute and log a daily summary snapshot.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from src.database import IranJobsDB

logger = logging.getLogger(__name__)

# Days without a sighting before a job is considered gone from the site.
_DEFAULT_STALE_DAYS = 14


class AnalyticsEngine:
    """
    Compute market analytics and maintain data freshness.

    Designed to run as a Cloud Run Job after every scraper + processor cycle.
    """

    def __init__(self, db: IranJobsDB, stale_days: int = _DEFAULT_STALE_DAYS):
        self.db = db
        self.conn = db.db_connection
        self.stale_days = stale_days

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """
        Execute the full analytics pipeline.

        Returns:
            Summary dict with counts and status.
        """
        process_id = "analytics_engine"
        logger.info("Analytics engine starting")
        self._log_event(process_id, "started", "Analytics job starting", 0, 0)

        try:
            # Step 1 — deactivate jobs not seen in recent scrapes
            deactivated = self._deactivate_stale_jobs()
            logger.info("Deactivated %d stale job postings", deactivated)

            # Step 2 — refresh company job counts + hiring velocity
            companies_updated = self._update_company_metrics()
            logger.info("Updated metrics for %d companies", companies_updated)

            # Step 3 — snapshot summary stats
            summary = self._compute_summary_stats()
            logger.info("Summary: %s", summary)

            result: dict[str, Any] = {
                "status": "completed",
                "deactivated_jobs": deactivated,
                "companies_updated": companies_updated,
                "summary": summary,
            }

            self._log_event(
                process_id,
                "completed",
                (
                    f"Analytics complete: deactivated={deactivated}, "
                    f"companies_updated={companies_updated}"
                ),
                records_processed=deactivated + companies_updated,
                records_failed=0,
                details=result,
            )
            return result

        except Exception as exc:
            logger.exception("Analytics engine failed")
            self._log_event(
                process_id,
                "failed",
                f"Analytics failed: {exc}",
                0,
                1,
                error_details=str(exc)[:2000],
            )
            raise

    # ------------------------------------------------------------------
    # Step 1 — Deactivate stale jobs
    # ------------------------------------------------------------------

    def _deactivate_stale_jobs(self) -> int:
        """
        Mark job postings as inactive if last_seen_date is older than
        `stale_days` days ago.

        Returns:
            Count of deactivated postings.
        """
        rows = self.conn.execute_write_returning(
            """
            WITH updated AS (
                UPDATE iran_jobs.job_postings
                SET is_active        = FALSE,
                    deactivated_date = CURRENT_DATE
                WHERE last_seen_date < CURRENT_DATE - %s
                  AND is_active = TRUE
                RETURNING id
            )
            SELECT COUNT(*)::int AS count FROM updated
            """,
            (self.stale_days,),
        )
        return rows[0]["count"] if rows else 0

    # ------------------------------------------------------------------
    # Step 2 — Company metrics
    # ------------------------------------------------------------------

    def _update_company_metrics(self) -> int:
        """
        Recompute active_job_postings and hiring_velocity_30d for every
        company that currently has active postings, then zero-out companies
        that have no active postings left.

        Returns:
            Number of companies with active postings.
        """
        counts = self.conn.fetchall(
            """
            SELECT
                company_id,
                COUNT(*)::int                                                     AS active_count,
                COUNT(*) FILTER (WHERE first_seen_date >= CURRENT_DATE - 30)::int AS count_30d,
                COUNT(*)::int                                                     AS total_count
            FROM iran_jobs.job_postings
            WHERE company_id IS NOT NULL
              AND is_active = TRUE
            GROUP BY company_id
            """
        )

        for row in counts:
            velocity = round(row["count_30d"] / 30.0, 4)
            self.conn.execute_with_transaction(
                """
                UPDATE iran_jobs.companies
                SET active_job_postings  = %s,
                    hiring_velocity_30d  = %s,
                    last_activity_date   = CURRENT_DATE,
                    updated_at           = NOW()
                WHERE id = %s
                """,
                (row["active_count"], velocity, row["company_id"]),
            )

        # Zero out companies that no longer have any active postings
        self.conn.execute_with_transaction(
            """
            UPDATE iran_jobs.companies
            SET active_job_postings = 0,
                hiring_velocity_30d = 0,
                updated_at          = NOW()
            WHERE active_job_postings > 0
              AND id NOT IN (
                  SELECT DISTINCT company_id
                  FROM iran_jobs.job_postings
                  WHERE company_id IS NOT NULL
                    AND is_active = TRUE
              )
            """
        )

        return len(counts)

    # ------------------------------------------------------------------
    # Step 3 — Summary snapshot
    # ------------------------------------------------------------------

    def _compute_summary_stats(self) -> dict[str, Any]:
        """Return aggregate counts across the whole job_postings table."""
        row = self.conn.fetchone(
            """
            SELECT
                COUNT(*)::int                                                          AS total_jobs,
                COUNT(*) FILTER (WHERE is_active = TRUE)::int                         AS active_jobs,
                COUNT(*) FILTER (WHERE first_seen_date >= CURRENT_DATE - 7)::int      AS new_last_7d,
                COUNT(*) FILTER (WHERE deactivated_date = CURRENT_DATE)::int          AS deactivated_today,
                COUNT(DISTINCT company_id)
                    FILTER (WHERE is_active = TRUE AND company_id IS NOT NULL)::int   AS active_companies,
                COUNT(*) FILTER (WHERE processing_status = 'processed')::int          AS processed_jobs,
                COUNT(*) FILTER (WHERE processing_status = 'pending')::int            AS pending_jobs
            FROM iran_jobs.job_postings
            """
        )
        return dict(row) if row else {}

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------

    def _log_event(
        self,
        process_id: str,
        status: str,
        message: str,
        records_processed: int,
        records_failed: int,
        details: dict[str, Any] | None = None,
        error_details: str | None = None,
    ) -> None:
        try:
            self.conn.execute_with_transaction(
                """
                INSERT INTO iran_jobs.processing_logs (
                    process_type, process_id, status, message,
                    details_json, records_processed, records_failed,
                    error_details, timestamp
                )
                VALUES ('analysis', %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    process_id,
                    status,
                    message,
                    json.dumps(details) if details else None,
                    records_processed,
                    records_failed,
                    error_details,
                ),
            )
        except Exception:
            logger.warning("Failed to write analytics log event", exc_info=True)
