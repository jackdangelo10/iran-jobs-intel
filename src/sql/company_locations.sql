CREATE TABLE company_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    company_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    
    -- Relationship type
    location_type TEXT CHECK (location_type IN ('headquarters', 'office', 'branch', 'remote_hub', 'subsidiary', 'unknown')) NOT NULL,
    
    -- Details
    office_name TEXT,                        -- "Tehran Main Office", "Mashhad Branch"
    employee_count_estimate INTEGER,         -- How many people at this location
    is_primary BOOLEAN DEFAULT FALSE,        -- Is this the main location?
    
    -- Address details (if available)
    address_persian TEXT,
    address_english TEXT,
    
    -- Operational status
    is_active BOOLEAN DEFAULT TRUE,
    established_date DATE,
    closed_date DATE,
    
    -- Processing
    confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id),
    
    UNIQUE(company_id, location_id, location_type),
    
    CREATE INDEX idx_company ON company_locations(company_id);
    CREATE INDEX idx_location ON company_locations(location_id);
    CREATE INDEX idx_primary ON company_locations(is_primary);
    CREATE INDEX idx_active ON company_locations(is_active);
);