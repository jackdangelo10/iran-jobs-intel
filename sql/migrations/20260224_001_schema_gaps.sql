-- Migration: 20260224_001_schema_gaps.sql
--
-- Adds columns that were introduced into schema.py after the initial
-- database deployment.  Safe to run multiple times — all statements
-- use ADD COLUMN IF NOT EXISTS so they are no-ops on a fresh DB.
--
-- Run against Supabase:
--   psql "$IRAN_JOBS_SCRAPER_DATABASE_URL" -f sql/migrations/20260224_001_schema_gaps.sql

-- ── 1. gender_requirement ─────────────────────────────────────────────────────
-- Added to job_postings to capture demographic requirements scraped from the
-- three job boards.  All three scrapers now write this field.
ALTER TABLE job_postings
    ADD COLUMN IF NOT EXISTS gender_requirement TEXT DEFAULT 'unknown';

-- ── 2. latitude on locations ──────────────────────────────────────────────────
-- The original schema.py had a syntax bug: the latitude column was defined as
-- just "NUMERIC," with no column name, causing a PostgreSQL parse error and
-- leaving the column absent.  This restores it.
ALTER TABLE locations
    ADD COLUMN IF NOT EXISTS latitude NUMERIC;

-- ── 3. Index on gender_requirement ───────────────────────────────────────────
-- schema.py already defines this index, but if the DB was created before
-- gender_requirement existed the index creation would have been skipped.
CREATE INDEX IF NOT EXISTS idx_gender_requirement
    ON job_postings (gender_requirement);
