-- Migration: 20260224_002_performance_indexes.sql
--
-- Adds indexes that are required by the dashboard API routes and the
-- analytics engine.  None of these exist in the original schema.py
-- job_postings_indexes block.
--
-- All six CREATE INDEX statements use IF NOT EXISTS so this is safe
-- to re-run at any time.
--
-- Run against Supabase:
--   psql "$IRAN_JOBS_SCRAPER_DATABASE_URL" -f sql/migrations/20260224_002_performance_indexes.sql

-- ── Dashboard API routes ──────────────────────────────────────────────────────
-- Every API route (/api/stats, /api/jobs-over-time, /api/top-companies, etc.)
-- filters with:  WHERE first_seen_date >= CURRENT_DATE - $days
CREATE INDEX IF NOT EXISTS idx_first_seen_date
    ON job_postings (first_seen_date);

-- Most routes also filter on source_site; the compound index lets Postgres
-- satisfy both predicates with a single index scan.
CREATE INDEX IF NOT EXISTS idx_source_site_first_seen
    ON job_postings (source_site, first_seen_date);

-- ── Analytics engine — job deactivation ──────────────────────────────────────
-- _deactivate_stale_jobs() runs:
--   WHERE last_seen_date < CURRENT_DATE - 14 AND is_active = TRUE
CREATE INDEX IF NOT EXISTS idx_last_seen_date
    ON job_postings (last_seen_date)
    WHERE is_active = TRUE;

-- ── Analytics engine — company metric refresh ────────────────────────────────
-- _update_company_metrics() aggregates:
--   WHERE company_id IS NOT NULL AND is_active = TRUE
-- and the 30-day velocity sub-count also references first_seen_date.
CREATE INDEX IF NOT EXISTS idx_company_active
    ON job_postings (company_id, is_active, first_seen_date)
    WHERE company_id IS NOT NULL;

-- ── Analytics engine — summary stats ────────────────────────────────────────
-- _compute_summary_stats() counts deactivated_date = CURRENT_DATE.
-- A partial index keeps it small.
CREATE INDEX IF NOT EXISTS idx_deactivated_date
    ON job_postings (deactivated_date)
    WHERE deactivated_date IS NOT NULL;

-- ── Processor — pending-job fetch ────────────────────────────────────────────
-- _get_pending_jobs() scans:
--   WHERE processing_status = 'pending' ORDER BY id ASC
-- processing_status is already indexed by schema.py, but adding source_site
-- helps the scraper-job discovery uniqueness check too.
CREATE INDEX IF NOT EXISTS idx_source_site
    ON job_postings (source_site);
