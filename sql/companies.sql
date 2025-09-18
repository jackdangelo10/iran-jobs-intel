CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Basic company information (bilingual)
    display_name_persian TEXT,
    display_name_english TEXT,
    canonical_name TEXT UNIQUE,  -- Canonical name for deduplication
    name_variations_json TEXT,    -- JSON array of all name variations we've seen
    
    -- Company identification
    company_registration_number TEXT,  -- Iranian company registration if available
    tax_id TEXT,
    website_url TEXT,
    linkedin_url TEXT,
    
    -- Classification
    company_type TEXT CHECK (company_type IN ('private', 'state_owned', 'semi_state', 'irgc_linked', 'foundation', 'cooperative', 'foreign', 'unknown')) DEFAULT 'unknown',
    parent_company_id INTEGER,  -- Self-referencing for subsidiaries
    
    -- Industry classification
    primary_sector TEXT,        -- ISIC codes or custom classification
    secondary_sectors_json TEXT, -- JSON array for multiple sectors
    business_description_persian TEXT,
    business_description_english TEXT,
    
    -- Size indicators
    employee_count_estimate INTEGER,
    employee_size_category TEXT CHECK (employee_size_category IN ('startup', 'small', 'medium', 'large', 'enterprise', 'unknown')) DEFAULT 'unknown',
    annual_revenue_estimate REAL,
    
    -- Geographic presence
    headquarters_location_id INTEGER,  -- FK to locations table
    locations_json TEXT,              -- JSON array of all operational locations
    
    -- Risk and compliance (as discussed in original spec)
    is_sanctioned BOOLEAN DEFAULT FALSE,
    sanction_programs_json TEXT,      -- JSON array of applicable sanctions
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'critical', 'unknown')) DEFAULT 'unknown',
    compliance_notes TEXT,
    
    -- Network analysis
    connected_entities_json TEXT,     -- Related companies, individuals
    government_contracts BOOLEAN DEFAULT FALSE,
    defense_related BOOLEAN DEFAULT FALSE,
    
    -- Company lifecycle
    founded_year INTEGER,
    first_seen_date DATE NOT NULL,
    last_activity_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Hiring metrics (computed fields)
    total_job_postings INTEGER DEFAULT 0,
    active_job_postings INTEGER DEFAULT 0,
    avg_posting_frequency REAL,       -- Posts per month
    hiring_velocity_30d REAL,         -- Recent hiring activity
    
    -- Processing status
    profile_completeness_score REAL CHECK (profile_completeness_score >= 0 AND profile_completeness_score <= 1),
    needs_manual_review BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_company_id) REFERENCES companies(id),
    FOREIGN KEY (headquarters_location_id) REFERENCES locations(id),
    
    CREATE INDEX idx_name_normalized ON companies(name_normalized);
    CREATE INDEX idx_company_type ON companies(company_type);
    CREATE INDEX idx_risk_level ON companies(risk_level);
    CREATE INDEX idx_sanctioned ON companies(is_sanctioned);
    CREATE INDEX idx_active ON companies(is_active);
    CREATE INDEX idx_hiring_activity ON companies(active_job_postings);
);