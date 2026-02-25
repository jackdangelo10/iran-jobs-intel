-- Create a dedicated role for the scraper and grant required privileges.
-- Run this as a superuser (e.g., postgres) in Supabase.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'iran_jobs_scraper') THEN
        CREATE ROLE iran_jobs_scraper LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
    END IF;
END $$;

-- Ensure the role can connect to the database
GRANT CONNECT ON DATABASE postgres TO iran_jobs_scraper;

-- Allow schema usage and object creation in public
GRANT USAGE, CREATE ON SCHEMA public TO iran_jobs_scraper;

-- Grant full access to existing tables and sequences in public
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iran_jobs_scraper;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iran_jobs_scraper;

-- Ensure future tables/sequences are accessible too
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON TABLES TO iran_jobs_scraper;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON SEQUENCES TO iran_jobs_scraper;
