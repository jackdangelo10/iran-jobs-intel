CREATE TABLE job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source tracking
    raw_scrape_id INTEGER,
    external_id TEXT,  -- Site's internal job ID
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    source_url TEXT NOT NULL,
    
    -- Job content (bilingual)
    title_persian TEXT NOT NULL,
    title_english TEXT,
    title_normalized TEXT,  -- Standardized for grouping/analysis
    description_persian TEXT,
    description_english TEXT,
    description_summary TEXT,  -- Key points extracted
    
    -- Company information (denormalized for now, normalize later)
    company_name_raw TEXT,  -- As scraped from job posting
    company_id INTEGER,     -- FK to companies table (filled during processing)
    
    -- Location (denormalized for now)
    location_raw TEXT,      -- As scraped
    location_id INTEGER,    -- FK to locations table (filled during processing)
    is_remote BOOLEAN DEFAULT FALSE,
    
    -- Employment details
    employment_type TEXT CHECK (employment_type IN ('full_time', 'part_time', 'contract', 'internship', 'freelance', 'unknown')) DEFAULT 'unknown',
    experience_level TEXT CHECK (experience_level IN ('entry', 'junior', 'mid', 'senior', 'lead', 'executive', 'unknown')) DEFAULT 'unknown',
    experience_years_min INTEGER,
    experience_years_max INTEGER,
    
    -- Education requirements
    education_level TEXT CHECK (education_level IN ('none', 'diploma', 'associate', 'bachelor', 'master', 'phd', 'unknown')) DEFAULT 'unknown',
    education_field TEXT,
    
    -- Salary (dual currency as we discussed)
    salary_min_original REAL,
    salary_max_original REAL,
    salary_currency_original TEXT DEFAULT 'IRR',
    salary_period TEXT CHECK (salary_period IN ('hourly', 'daily', 'monthly', 'yearly', 'project', 'unknown')) DEFAULT 'unknown',
    
    -- Converted salaries (for analysis)
    salary_min_irr REAL,
    salary_max_irr REAL,
    salary_min_usd REAL,
    salary_max_usd REAL,
    exchange_rate_used REAL,  -- IRR to USD rate when converted
    exchange_rate_date DATE,
    
    -- Skills (JSON for speed + normalized relationships for analysis)
    skills_required_json TEXT,  -- JSON array for quick access
    skills_preferred_json TEXT,
    technologies_mentioned_json TEXT,
    
    -- Processing metadata
    data_quality_score REAL CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    processing_confidence REAL CHECK (processing_confidence >= 0 AND processing_confidence <= 1),
    manual_review_needed BOOLEAN DEFAULT FALSE,
    
    -- Temporal tracking
    posted_date DATE,
    application_deadline DATE,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    deactivated_date DATE,
    
    -- Processing status
    processing_status TEXT CHECK (processing_status IN ('pending', 'processed', 'failed', 'skipped')) DEFAULT 'pending',
    
    FOREIGN KEY (raw_scrape_id) REFERENCES raw_scrapes(id),
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    
    UNIQUE(source_site, external_id),
    
    CREATE INDEX idx_company_name ON job_postings(company_name_raw);
    CREATE INDEX idx_posted_date ON job_postings(posted_date);
    CREATE INDEX idx_active ON job_postings(is_active);
    CREATE INDEX idx_processing_status ON job_postings(processing_status);
    CREATE INDEX idx_employment_type ON job_postings(employment_type);
    CREATE INDEX idx_experience_level ON job_postings(experience_level);
);