-- Track per-site discovery pagination progress for crash-resume behavior.
-- Run this as a superuser (e.g., postgres) in Supabase.

CREATE TABLE IF NOT EXISTS scrape_progress (
    id BIGSERIAL PRIMARY KEY,
    source_site TEXT NOT NULL UNIQUE,
    last_success_page INTEGER NOT NULL DEFAULT 0,
    last_success_at TIMESTAMP DEFAULT NOW(),
    last_session_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_scrape_progress_site ON scrape_progress(source_site);
