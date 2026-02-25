-- Iran Jobs Intelligence Platform - Full Schema
-- Run this once in Supabase SQL Editor to create all tables.
-- Tables are created in the public schema.

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
    country TEXT DEFAULT 'Iran',
    province_persian TEXT,
    province_english TEXT,
    city_persian TEXT,
    city_english TEXT,
    district_persian TEXT,
    district_english TEXT,
    location_normalized TEXT UNIQUE,
    location_type TEXT CHECK (location_type IN ('country', 'province', 'city', 'district', 'industrial_zone', 'free_trade_zone')),
    latitude NUMERIC,
    longitude NUMERIC,
    economic_zone_type TEXT CHECK (economic_zone_type IN ('regular', 'special_economic_zone', 'free_trade_zone', 'industrial_park', 'unknown')) DEFAULT 'regular',
    development_level TEXT CHECK (development_level IN ('developed', 'developing', 'underdeveloped', 'unknown')) DEFAULT 'unknown',
    iso_province_code TEXT,
    postal_code_prefix TEXT,
    location_variations_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_normalized ON locations(location_normalized);
CREATE INDEX IF NOT EXISTS idx_province ON locations(province_english);
CREATE INDEX IF NOT EXISTS idx_city ON locations(city_english);
CREATE INDEX IF NOT EXISTS idx_coordinates ON locations(latitude, longitude);

-- ============================================================================
-- SKILLS
-- ============================================================================

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    skill_name_english TEXT UNIQUE NOT NULL,
    skill_name_persian TEXT,
    skill_aliases_json JSONB,
    skill_category TEXT CHECK (skill_category IN ('technical', 'soft', 'language', 'certification', 'tool', 'framework', 'methodology', 'domain_knowledge')) NOT NULL,
    skill_subcategory TEXT,
    technology_domain TEXT,
    skill_level TEXT CHECK (skill_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',
    learning_curve TEXT CHECK (learning_curve IN ('easy', 'medium', 'hard', 'very_hard', 'unknown')) DEFAULT 'unknown',
    is_dual_use BOOLEAN DEFAULT FALSE,
    export_control_classification TEXT,
    strategic_importance TEXT CHECK (strategic_importance IN ('low', 'medium', 'high', 'critical', 'unknown')) DEFAULT 'low',
    primary_industries_json JSONB,
    skill_description TEXT,
    parent_skill_id INTEGER,
    related_skills_json JSONB,
    prerequisite_skills_json JSONB,
    confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    needs_verification BOOLEAN DEFAULT FALSE,
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (parent_skill_id) REFERENCES skills(id)
);

CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(skill_name_english);
CREATE INDEX IF NOT EXISTS idx_category ON skills(skill_category, skill_subcategory);
CREATE INDEX IF NOT EXISTS idx_dual_use ON skills(is_dual_use, strategic_importance);
CREATE INDEX IF NOT EXISTS idx_active ON skills(is_active);

-- ============================================================================
-- COMPANIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    display_name_persian TEXT,
    display_name_english TEXT,
    canonical_name TEXT UNIQUE,
    name_variations_json JSONB,
    company_registration_number TEXT,
    tax_id TEXT,
    website_url TEXT,
    linkedin_url TEXT,
    company_type TEXT CHECK (company_type IN ('private', 'state_owned', 'semi_state', 'irgc_linked', 'foundation', 'cooperative', 'foreign', 'unknown')) DEFAULT 'unknown',
    parent_company_id INTEGER,
    primary_sector TEXT,
    secondary_sectors_json JSONB,
    business_description_persian TEXT,
    business_description_english TEXT,
    employee_count_estimate INTEGER,
    employee_size_category TEXT CHECK (employee_size_category IN ('startup', 'small', 'medium', 'large', 'enterprise', 'unknown')) DEFAULT 'unknown',
    annual_revenue_estimate NUMERIC,
    headquarters_location_id INTEGER,
    locations_json JSONB,
    is_sanctioned BOOLEAN DEFAULT FALSE,
    sanction_programs_json JSONB,
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'critical', 'unknown')) DEFAULT 'unknown',
    compliance_notes TEXT,
    connected_entities_json JSONB,
    government_contracts BOOLEAN DEFAULT FALSE,
    defense_related BOOLEAN DEFAULT FALSE,
    founded_year INTEGER,
    first_seen_date DATE NOT NULL,
    last_activity_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    total_job_postings INTEGER DEFAULT 0,
    active_job_postings INTEGER DEFAULT 0,
    avg_posting_frequency NUMERIC,
    hiring_velocity_30d NUMERIC,
    profile_completeness_score NUMERIC CHECK (profile_completeness_score >= 0 AND profile_completeness_score <= 1),
    needs_manual_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (parent_company_id) REFERENCES companies(id),
    FOREIGN KEY (headquarters_location_id) REFERENCES locations(id)
);

CREATE INDEX IF NOT EXISTS idx_canonical_name ON companies(canonical_name);
CREATE INDEX IF NOT EXISTS idx_company_type ON companies(company_type);
CREATE INDEX IF NOT EXISTS idx_risk_level ON companies(risk_level);
CREATE INDEX IF NOT EXISTS idx_sanctioned ON companies(is_sanctioned);
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
    description_summary TEXT,
    company_name_raw TEXT,
    company_url TEXT,
    company_id INTEGER,
    location_raw TEXT,
    location_id INTEGER,
    is_remote BOOLEAN DEFAULT FALSE,
    employment_type TEXT DEFAULT 'unknown',
    experience_level TEXT DEFAULT 'unknown',
    experience_years_min INTEGER,
    experience_years_max INTEGER,
    gender_requirement TEXT DEFAULT 'unknown',
    education_level TEXT DEFAULT 'unknown',
    education_field TEXT,
    salary_min_original NUMERIC,
    salary_max_original NUMERIC,
    salary_currency_original TEXT DEFAULT 'IRR',
    salary_period TEXT DEFAULT 'unknown',
    salary_min_irr NUMERIC,
    salary_max_irr NUMERIC,
    salary_min_usd NUMERIC,
    salary_max_usd NUMERIC,
    exchange_rate_used NUMERIC,
    exchange_rate_date DATE,
    skills_required_json JSONB,
    skills_preferred_json JSONB,
    technologies_mentioned_json JSONB,
    data_quality_score NUMERIC CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    processing_confidence NUMERIC CHECK (processing_confidence >= 0 AND processing_confidence <= 1),
    manual_review_needed BOOLEAN DEFAULT FALSE,
    posted_date DATE,
    application_deadline DATE,
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
CREATE INDEX IF NOT EXISTS idx_gender_requirement ON job_postings(gender_requirement);
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
    years_experience INTEGER,
    mention_context TEXT,
    confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    extraction_method TEXT CHECK (extraction_method IN ('keyword_match', 'nlp_extraction', 'manual_review')) DEFAULT 'keyword_match',
    verified BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (job_posting_id) REFERENCES job_postings(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    UNIQUE(job_posting_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_job ON job_skills(job_posting_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_requirement_type ON job_skills(requirement_type);
CREATE INDEX IF NOT EXISTS idx_confidence ON job_skills(confidence_score);

-- ============================================================================
-- COMPANY LOCATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_locations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    location_type TEXT CHECK (location_type IN ('headquarters', 'office', 'branch', 'remote_hub', 'subsidiary', 'unknown')) NOT NULL,
    office_name TEXT,
    employee_count_estimate INTEGER,
    is_primary BOOLEAN DEFAULT FALSE,
    address_persian TEXT,
    address_english TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    established_date DATE,
    closed_date DATE,
    confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id),
    UNIQUE(company_id, location_id, location_type)
);

CREATE INDEX IF NOT EXISTS idx_company_locations_company ON company_locations(company_id);
CREATE INDEX IF NOT EXISTS idx_company_locations_location ON company_locations(location_id);
CREATE INDEX IF NOT EXISTS idx_company_locations_primary ON company_locations(is_primary);
CREATE INDEX IF NOT EXISTS idx_company_locations_active ON company_locations(is_active);

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
    processing_time_ms INTEGER,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_code TEXT,
    error_details TEXT,
    stack_trace TEXT,
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
    usage_count INTEGER DEFAULT 1,
    is_verified BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_hash_lookup ON translation_cache(source_text_hash);
CREATE INDEX IF NOT EXISTS idx_usage ON translation_cache(last_used_at, usage_count);
CREATE INDEX IF NOT EXISTS idx_language_pair ON translation_cache(source_language, target_language);
