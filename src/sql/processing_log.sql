CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Process identification
    process_type TEXT CHECK (process_type IN ('scraping', 'processing', 'translation', 'entity_resolution', 'analysis')) NOT NULL,
    process_id TEXT,                      -- UUID for grouping related log entries
    scrape_session_id TEXT,               -- Link to scrape session
    
    -- Entity processed
    entity_type TEXT CHECK (entity_type IN ('scrape_session', 'job_posting', 'company', 'raw_scrape', 'batch')),
    entity_id INTEGER,                    -- ID of the entity being processed
    
    -- Status and results
    status TEXT CHECK (status IN ('started', 'completed', 'failed', 'warning', 'skipped')) NOT NULL,
    message TEXT,                         -- Human readable message
    details_json TEXT,                    -- Structured details
    
    -- Performance metrics
    processing_time_ms INTEGER,           -- How long it took
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Error details
    error_code TEXT,
    error_details TEXT,
    stack_trace TEXT,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CREATE INDEX idx_process_type ON processing_logs(process_type, status);
    CREATE INDEX idx_session ON processing_logs(scrape_session_id);
    CREATE INDEX idx_timestamp ON processing_logs(timestamp);
    CREATE INDEX idx_entity ON processing_logs(entity_type, entity_id);
);