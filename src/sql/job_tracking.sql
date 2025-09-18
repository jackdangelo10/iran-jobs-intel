CREATE TABLE job_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    job_url TEXT UNIQUE NOT NULL,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    
    -- Lifecycle tracking
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    disappeared_date DATE,
    disappeared_session TEXT,
    
    -- Scraping status
    detail_scraped BOOLEAN DEFAULT FALSE,
    last_detail_scrape_date DATE,
    detail_scrape_count INTEGER DEFAULT 0,
    
    CREATE INDEX idx_job_url ON job_tracking(job_url);
    CREATE INDEX idx_active ON job_tracking(is_active);
    CREATE INDEX idx_last_seen ON job_tracking(last_seen_date);
);