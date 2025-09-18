CREATE TABLE company_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    company_url TEXT UNIQUE NOT NULL,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    
    -- Lifecycle
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,  
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    
    -- Scraping status
    profile_scraped BOOLEAN DEFAULT FALSE,
    last_profile_scrape_date DATE,
    profile_scrape_count INTEGER DEFAULT 0,
    
    CREATE INDEX idx_company_url ON company_tracking(company_url);
    CREATE INDEX idx_last_seen ON company_tracking(last_seen_date);
);