-- 005_reset_all_data.sql
-- WARNING: Destructive migration for development/testing use.
-- This clears all operational data and resets identity sequences.

BEGIN;

TRUNCATE TABLE
    processing_logs,
    translation_cache,
    job_skills,
    company_locations,
    job_postings,
    raw_scrapes,
    job_discoveries,
    job_tracking,
    company_tracking,
    companies,
    skills,
    locations
RESTART IDENTITY CASCADE;

COMMIT;
