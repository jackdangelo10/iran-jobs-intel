CREATE TABLE location_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    
    -- Computed metrics
    total_companies INTEGER DEFAULT 0,
    active_job_postings INTEGER DEFAULT 0,
    avg_salary_irr REAL,
    
    -- Time-bound
    metrics_date DATE NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (location_id) REFERENCES locations(id),
    UNIQUE(location_id, metrics_date)
);