-- Allow the scraper role to read/write all rows in all app tables.
-- Run this as a superuser (e.g., postgres) in Supabase.

DO $$
DECLARE
    t text;
    tables text[] := ARRAY[
        'raw_scrapes',
        'locations',
        'skills',
        'companies',
        'job_postings',
        'job_discoveries',
        'job_tracking',
        'job_skills',
        'company_locations',
        'company_tracking',
        'processing_logs',
        'translation_cache'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        -- Create an "allow all" policy for the scraper role if missing
        IF NOT EXISTS (
            SELECT 1
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = t
              AND policyname = 'allow_scraper_all'
        ) THEN
            EXECUTE format(
                'CREATE POLICY allow_scraper_all ON public.%I FOR ALL TO iran_jobs_scraper USING (true) WITH CHECK (true)',
                t
            );
        END IF;
    END LOOP;
END $$;
