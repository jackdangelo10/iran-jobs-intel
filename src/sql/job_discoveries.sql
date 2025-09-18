CREATE TABLE job_discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_session_id TEXT NOT NULL,
    
    -- What we discovered
    job_url TEXT NOT NULL,
    company_url TEXT,  -- Company profile link from the job listing
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    
    -- Where we found it
    found_on_page TEXT,  -- Which job list page URL
    
    -- Tracking
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(scrape_session_id, job_url),
    
    CREATE INDEX idx_session ON job_discoveries(scrape_session_id);
    CREATE INDEX idx_job_url ON job_discoveries(job_url);
);