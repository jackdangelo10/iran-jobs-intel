CREATE TABLE raw_scrapes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source identification  
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    source_url TEXT NOT NULL,
    page_type TEXT CHECK (page_type IN ('job_list', 'job_detail', 'company_profile')),
    
    -- Session tracking
    scrape_session_id TEXT,
    
    -- Content
    raw_html TEXT,
    html_size INTEGER,
    response_status INTEGER DEFAULT 200,
    content_hash TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    
    -- Processing status
    processing_status TEXT CHECK (processing_status IN ('pending', 'processed', 'failed', 'skipped')) DEFAULT 'pending',
    error_message TEXT,
    
    -- Metadata
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CREATE INDEX idx_scrape_session ON raw_scrapes(scrape_session_id);
    CREATE INDEX idx_processing_status ON raw_scrapes(processing_status);
    CREATE INDEX idx_scraped_date ON raw_scrapes(scraped_at);
    CREATE INDEX idx_content_hash ON raw_scrapes(content_hash);
);