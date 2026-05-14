-- Iran Jobs Intelligence Platform - Full Schema
-- Run this once in Supabase SQL Editor to create all tables.
-- Tables are created in the public schema.
--
-- Trimmed (migration 006): only columns the pipeline actually reads or writes.

-- ============================================================================
-- RAW SCRAPES
-- ============================================================================

CREATE TABLE IF NOT EXISTS raw_scrapes (
    id BIGSERIAL PRIMARY KEY,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    source_url TEXT NOT NULL,
    page_type TEXT CHECK (page_type IN ('job_list', 'job_detail', 'company_profile')),
    scrape_session_id TEXT,
    raw_html TEXT,
    html_size INTEGER,
    response_status INTEGER DEFAULT 200,
    content_hash TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    processing_status TEXT CHECK (processing_status IN ('pending', 'processed', 'failed', 'skipped')) DEFAULT 'pending',
    error_message TEXT,
    scraped_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrape_session ON raw_scrapes(scrape_session_id);
CREATE INDEX IF NOT EXISTS idx_processing_status ON raw_scrapes(processing_status);
CREATE INDEX IF NOT EXISTS idx_scraped_date ON raw_scrapes(scraped_at);
CREATE INDEX IF NOT EXISTS idx_content_hash ON raw_scrapes(content_hash);

-- ============================================================================
-- LOCATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    city_persian TEXT,
    location_normalized TEXT UNIQUE,
    location_type TEXT CHECK (location_type IN ('country', 'province', 'city', 'district', 'industrial_zone', 'free_trade_zone')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_normalized ON locations(location_normalized);

-- ============================================================================
-- SKILLS
-- ============================================================================

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    skill_name_english TEXT UNIQUE NOT NULL,
    skill_category TEXT CHECK (skill_category IN (
        'language', 'framework', 'database', 'cloud',
        'tool', 'methodology', 'soft', 'certification', 'domain_knowledge'
    )) NOT NULL,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(skill_name_english);
CREATE INDEX IF NOT EXISTS idx_skill_category ON skills(skill_category);
CREATE INDEX IF NOT EXISTS idx_skill_active ON skills(is_active);

-- ============================================================================
-- COMPANIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    display_name_persian TEXT,
    canonical_name TEXT UNIQUE,
    first_seen_date DATE NOT NULL,
    last_activity_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    total_job_postings INTEGER DEFAULT 0,
    active_job_postings INTEGER DEFAULT 0,
    hiring_velocity_30d NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_canonical_name ON companies(canonical_name);
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);
CREATE INDEX IF NOT EXISTS idx_hiring_activity ON companies(active_job_postings);

-- ============================================================================
-- JOB POSTINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_postings (
    id BIGSERIAL PRIMARY KEY,
    raw_scrape_id BIGINT,
    external_id TEXT,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    source_url TEXT NOT NULL,
    title_persian TEXT NOT NULL,
    title_english TEXT,
    title_normalized TEXT,
    description_persian TEXT,
    description_english TEXT,
    company_name_raw TEXT,
    company_url TEXT,
    company_id INTEGER,
    location_raw TEXT,
    location_id INTEGER,
    employment_type TEXT DEFAULT 'unknown',
    experience_level TEXT DEFAULT 'unknown',
    gender_requirement TEXT DEFAULT 'unknown',
    education_level TEXT DEFAULT 'unknown',
    salary_min_original NUMERIC,
    salary_max_original NUMERIC,
    salary_currency_original TEXT DEFAULT 'IRR',
    skills_required_json JSONB,
    skills_preferred_json JSONB,
    technologies_mentioned_json JSONB,
    posted_date DATE,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    deactivated_date DATE,
    processing_status TEXT CHECK (processing_status IN ('pending', 'processed', 'failed', 'skipped')) DEFAULT 'pending',
    FOREIGN KEY (raw_scrape_id) REFERENCES raw_scrapes(id),
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    UNIQUE(source_site, external_id)
);

CREATE INDEX IF NOT EXISTS idx_company_name ON job_postings(company_name_raw);
CREATE INDEX IF NOT EXISTS idx_posted_date ON job_postings(posted_date);
CREATE INDEX IF NOT EXISTS idx_job_postings_active ON job_postings(is_active);
CREATE INDEX IF NOT EXISTS idx_job_processing_status ON job_postings(processing_status);
CREATE INDEX IF NOT EXISTS idx_employment_type ON job_postings(employment_type);
CREATE INDEX IF NOT EXISTS idx_experience_level ON job_postings(experience_level);
CREATE INDEX IF NOT EXISTS idx_first_seen_date ON job_postings(first_seen_date);
CREATE INDEX IF NOT EXISTS idx_source_site_first_seen ON job_postings(source_site, first_seen_date);
CREATE INDEX IF NOT EXISTS idx_last_seen_date ON job_postings(last_seen_date) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_company_active ON job_postings(company_id, is_active, first_seen_date) WHERE company_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_deactivated_date ON job_postings(deactivated_date) WHERE deactivated_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_site ON job_postings(source_site);

-- ============================================================================
-- JOB DISCOVERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_discoveries (
    id BIGSERIAL PRIMARY KEY,
    scrape_session_id TEXT NOT NULL,
    job_url TEXT NOT NULL,
    company_url TEXT,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    found_on_page TEXT,
    discovered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(scrape_session_id, job_url)
);

CREATE INDEX IF NOT EXISTS idx_discoveries_session ON job_discoveries(scrape_session_id);
CREATE INDEX IF NOT EXISTS idx_discoveries_job_url ON job_discoveries(job_url);

-- ============================================================================
-- JOB TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_tracking (
    id SERIAL PRIMARY KEY,
    job_url TEXT UNIQUE NOT NULL,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    disappeared_date DATE,
    disappeared_session TEXT,
    detail_scraped BOOLEAN DEFAULT FALSE,
    last_detail_scrape_date DATE,
    detail_scrape_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tracking_job_url ON job_tracking(job_url);
CREATE INDEX IF NOT EXISTS idx_tracking_active ON job_tracking(is_active);
CREATE INDEX IF NOT EXISTS idx_tracking_last_seen ON job_tracking(last_seen_date);

-- ============================================================================
-- JOB SKILLS
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_skills (
    id BIGSERIAL PRIMARY KEY,
    job_posting_id BIGINT NOT NULL,
    skill_id INTEGER NOT NULL,
    requirement_type TEXT CHECK (requirement_type IN ('required', 'preferred', 'nice_to_have', 'mentioned')) NOT NULL,
    proficiency_level TEXT CHECK (proficiency_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',
    confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    extraction_method TEXT CHECK (extraction_method IN ('keyword_match', 'nlp_extraction', 'manual_review')) DEFAULT 'keyword_match',
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (job_posting_id) REFERENCES job_postings(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    UNIQUE(job_posting_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_job ON job_skills(job_posting_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_requirement_type ON job_skills(requirement_type);

-- ============================================================================
-- COMPANY TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_tracking (
    id SERIAL PRIMARY KEY,
    company_url TEXT UNIQUE NOT NULL,
    source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
    first_seen_session TEXT NOT NULL,
    last_seen_session TEXT NOT NULL,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    profile_scraped BOOLEAN DEFAULT FALSE,
    last_profile_scrape_date DATE,
    profile_scrape_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_company_url ON company_tracking(company_url);
CREATE INDEX IF NOT EXISTS idx_company_tracking_last_seen ON company_tracking(last_seen_date);

-- ============================================================================
-- PROCESSING LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS processing_logs (
    id BIGSERIAL PRIMARY KEY,
    process_type TEXT CHECK (process_type IN ('scraping', 'processing', 'translation', 'entity_resolution', 'analysis')) NOT NULL,
    process_id TEXT,
    scrape_session_id TEXT,
    entity_type TEXT CHECK (entity_type IN ('scrape_session', 'job_posting', 'company', 'raw_scrape', 'batch')),
    entity_id BIGINT,
    status TEXT CHECK (status IN ('started', 'completed', 'failed', 'warning', 'skipped')) NOT NULL,
    message TEXT,
    details_json JSONB,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_details TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_process_type ON processing_logs(process_type, status);
CREATE INDEX IF NOT EXISTS idx_logs_session ON processing_logs(scrape_session_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON processing_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_entity ON processing_logs(entity_type, entity_id);

-- ============================================================================
-- TRANSLATION CACHE
-- ============================================================================

CREATE TABLE IF NOT EXISTS translation_cache (
    id BIGSERIAL PRIMARY KEY,
    source_text_hash TEXT UNIQUE NOT NULL,
    source_text TEXT NOT NULL,
    source_language TEXT DEFAULT 'fa',
    target_language TEXT DEFAULT 'en',
    translated_text TEXT,
    translation_service TEXT DEFAULT 'google',
    translation_confidence NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    usage_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_hash_lookup ON translation_cache(source_text_hash);
CREATE INDEX IF NOT EXISTS idx_usage ON translation_cache(last_used_at, usage_count);
CREATE INDEX IF NOT EXISTS idx_language_pair ON translation_cache(source_language, target_language);

-- ============================================================================
-- SCRAPE PROGRESS
-- ============================================================================

CREATE TABLE IF NOT EXISTS scrape_progress (
    id BIGSERIAL PRIMARY KEY,
    source_site TEXT NOT NULL UNIQUE,
    last_success_page INTEGER NOT NULL DEFAULT 0,
    last_success_at TIMESTAMP DEFAULT NOW(),
    last_session_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_scrape_progress_site ON scrape_progress(source_site);
