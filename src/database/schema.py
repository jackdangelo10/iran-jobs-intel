# src/database/schema.py
"""
PostgreSQL database schema for Iran Jobs Intelligence Platform.
All tables are created in the public schema.

Trimmed (migration 006): removed aspirational columns that no code populates.
What remains here is what the scraper, processor, analytics, and dashboard
actually read or write.
"""

SCHEMA_SQL = {
    'raw_scrapes': """
        CREATE TABLE IF NOT EXISTS raw_scrapes (
            id BIGSERIAL PRIMARY KEY,

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
            scraped_at TIMESTAMP DEFAULT NOW()
        );
    """,

    'raw_scrapes_indexes': """
        CREATE INDEX IF NOT EXISTS idx_scrape_session ON raw_scrapes(scrape_session_id);
        CREATE INDEX IF NOT EXISTS idx_processing_status ON raw_scrapes(processing_status);
        CREATE INDEX IF NOT EXISTS idx_scraped_date ON raw_scrapes(scraped_at);
        CREATE INDEX IF NOT EXISTS idx_content_hash ON raw_scrapes(content_hash);
    """,

    'locations': """
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,

            -- Iranian admin hierarchy (only city_persian is populated today)
            city_persian TEXT,

            -- Standardized location
            location_normalized TEXT UNIQUE,
            location_type TEXT CHECK (location_type IN ('country', 'province', 'city', 'district', 'industrial_zone', 'free_trade_zone')),

            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """,

    'locations_indexes': """
        CREATE INDEX IF NOT EXISTS idx_normalized ON locations(location_normalized);
    """,

    'skills': """
        CREATE TABLE IF NOT EXISTS skills (
            id SERIAL PRIMARY KEY,

            -- Skill identification
            skill_name_english TEXT UNIQUE NOT NULL,

            -- Classification (populated from JobProcessor.SKILL_PATTERNS)
            skill_category TEXT CHECK (skill_category IN (
                'language', 'framework', 'database', 'cloud',
                'tool', 'methodology', 'soft', 'certification', 'domain_knowledge'
            )) NOT NULL,

            -- Lifecycle
            first_seen_date DATE NOT NULL,
            last_seen_date DATE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,

            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """,

    'skills_indexes': """
        CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(skill_name_english);
        CREATE INDEX IF NOT EXISTS idx_skill_category ON skills(skill_category);
        CREATE INDEX IF NOT EXISTS idx_skill_active ON skills(is_active);
    """,

    'companies': """
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,

            -- Canonical name + display
            display_name_persian TEXT,
            canonical_name TEXT UNIQUE,

            -- Lifecycle
            first_seen_date DATE NOT NULL,
            last_activity_date DATE,
            is_active BOOLEAN DEFAULT TRUE,

            -- Hiring metrics (refreshed by analytics_job)
            total_job_postings INTEGER DEFAULT 0,
            active_job_postings INTEGER DEFAULT 0,
            hiring_velocity_30d NUMERIC,

            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """,

    'companies_indexes': """
        CREATE INDEX IF NOT EXISTS idx_canonical_name ON companies(canonical_name);
        CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);
        CREATE INDEX IF NOT EXISTS idx_hiring_activity ON companies(active_job_postings);
    """,

    'job_postings': """
        CREATE TABLE IF NOT EXISTS job_postings (
            id BIGSERIAL PRIMARY KEY,

            -- Source tracking
            raw_scrape_id BIGINT,
            external_id TEXT,
            source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),
            source_url TEXT NOT NULL,

            -- Job content
            title_persian TEXT NOT NULL,
            title_english TEXT,
            title_normalized TEXT,
            description_persian TEXT,
            description_english TEXT,

            -- Company information
            company_name_raw TEXT,
            company_url TEXT,
            company_id INTEGER,

            -- Location
            location_raw TEXT,
            location_id INTEGER,

            -- Employment details
            employment_type TEXT DEFAULT 'unknown',
            experience_level TEXT DEFAULT 'unknown',

            -- Demographics (scraped, but not yet surfaced in dashboard)
            gender_requirement TEXT DEFAULT 'unknown',

            -- Education (scraped by Jobinja only, not yet surfaced)
            education_level TEXT DEFAULT 'unknown',

            -- Salary (original currency only; conversion not implemented)
            salary_min_original NUMERIC,
            salary_max_original NUMERIC,
            salary_currency_original TEXT DEFAULT 'IRR',

            -- Skills (JSONB sidecars, also normalized into job_skills)
            skills_required_json JSONB,
            skills_preferred_json JSONB,
            technologies_mentioned_json JSONB,

            -- Temporal tracking
            posted_date DATE,
            first_seen_date DATE NOT NULL,
            last_seen_date DATE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            deactivated_date DATE,

            -- Processing status
            processing_status TEXT CHECK (processing_status IN ('pending', 'processed', 'failed', 'skipped')) DEFAULT 'pending',

            FOREIGN KEY (raw_scrape_id) REFERENCES raw_scrapes(id),
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (location_id) REFERENCES locations(id),

            UNIQUE(source_site, external_id)
        );
    """,

    'job_postings_indexes': """
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
    """,

    'job_discoveries': """
        CREATE TABLE IF NOT EXISTS job_discoveries (
            id BIGSERIAL PRIMARY KEY,
            scrape_session_id TEXT NOT NULL,

            -- What we discovered
            job_url TEXT NOT NULL,
            company_url TEXT,
            source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),

            -- Where we found it
            found_on_page TEXT,

            -- Tracking
            discovered_at TIMESTAMP DEFAULT NOW(),

            UNIQUE(scrape_session_id, job_url)
        );
    """,

    'job_discoveries_indexes': """
        CREATE INDEX IF NOT EXISTS idx_discoveries_session ON job_discoveries(scrape_session_id);
        CREATE INDEX IF NOT EXISTS idx_discoveries_job_url ON job_discoveries(job_url);
    """,

    'job_tracking': """
        CREATE TABLE IF NOT EXISTS job_tracking (
            id SERIAL PRIMARY KEY,

            job_url TEXT UNIQUE NOT NULL,
            source_site TEXT NOT NULL CHECK (source_site IN ('irantalent', 'jobvision', 'jobinja')),

            -- Lifecycle tracking
            first_seen_session TEXT NOT NULL,
            last_seen_session TEXT NOT NULL,
            first_seen_date DATE NOT NULL,
            last_seen_date DATE NOT NULL,

            -- Status
            is_active BOOLEAN DEFAULT TRUE,
            disappeared_date DATE,
            disappeared_session TEXT,

            -- Scraping status
            detail_scraped BOOLEAN DEFAULT FALSE,
            last_detail_scrape_date DATE,
            detail_scrape_count INTEGER DEFAULT 0
        );
    """,

    'job_tracking_indexes': """
        CREATE INDEX IF NOT EXISTS idx_tracking_job_url ON job_tracking(job_url);
        CREATE INDEX IF NOT EXISTS idx_tracking_active ON job_tracking(is_active);
        CREATE INDEX IF NOT EXISTS idx_tracking_last_seen ON job_tracking(last_seen_date);
    """,

    'job_skills': """
        CREATE TABLE IF NOT EXISTS job_skills (
            id BIGSERIAL PRIMARY KEY,

            job_posting_id BIGINT NOT NULL,
            skill_id INTEGER NOT NULL,

            -- Requirement details
            requirement_type TEXT CHECK (requirement_type IN ('required', 'preferred', 'nice_to_have', 'mentioned')) NOT NULL,
            proficiency_level TEXT CHECK (proficiency_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',

            -- Extraction context
            confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
            extraction_method TEXT CHECK (extraction_method IN ('keyword_match', 'nlp_extraction', 'manual_review')) DEFAULT 'keyword_match',

            created_at TIMESTAMP DEFAULT NOW(),

            FOREIGN KEY (job_posting_id) REFERENCES job_postings(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(id),

            UNIQUE(job_posting_id, skill_id)
        );
    """,

    'job_skills_indexes': """
        CREATE INDEX IF NOT EXISTS idx_job_skills_job ON job_skills(job_posting_id);
        CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);
        CREATE INDEX IF NOT EXISTS idx_requirement_type ON job_skills(requirement_type);
    """,

    'company_tracking': """
        CREATE TABLE IF NOT EXISTS company_tracking (
            id SERIAL PRIMARY KEY,

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
            profile_scrape_count INTEGER DEFAULT 0
        );
    """,

    'company_tracking_indexes': """
        CREATE INDEX IF NOT EXISTS idx_company_url ON company_tracking(company_url);
        CREATE INDEX IF NOT EXISTS idx_company_tracking_last_seen ON company_tracking(last_seen_date);
    """,

    'processing_logs': """
        CREATE TABLE IF NOT EXISTS processing_logs (
            id BIGSERIAL PRIMARY KEY,

            -- Process identification
            process_type TEXT CHECK (process_type IN ('scraping', 'processing', 'translation', 'entity_resolution', 'analysis')) NOT NULL,
            process_id TEXT,
            scrape_session_id TEXT,

            -- Entity processed
            entity_type TEXT CHECK (entity_type IN ('scrape_session', 'job_posting', 'company', 'raw_scrape', 'batch')),
            entity_id BIGINT,

            -- Status and results
            status TEXT CHECK (status IN ('started', 'completed', 'failed', 'warning', 'skipped')) NOT NULL,
            message TEXT,
            details_json JSONB,

            -- Performance metrics
            records_processed INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,

            -- Error details
            error_details TEXT,

            timestamp TIMESTAMP DEFAULT NOW()
        );
    """,

    'processing_logs_indexes': """
        CREATE INDEX IF NOT EXISTS idx_process_type ON processing_logs(process_type, status);
        CREATE INDEX IF NOT EXISTS idx_logs_session ON processing_logs(scrape_session_id);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON processing_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_entity ON processing_logs(entity_type, entity_id);
    """,

    'translation_cache': """
        CREATE TABLE IF NOT EXISTS translation_cache (
            id BIGSERIAL PRIMARY KEY,

            -- Source content
            source_text_hash TEXT UNIQUE NOT NULL,
            source_text TEXT NOT NULL,
            source_language TEXT DEFAULT 'fa',
            target_language TEXT DEFAULT 'en',

            -- Translation result
            translated_text TEXT,
            translation_service TEXT DEFAULT 'google',
            translation_confidence NUMERIC,

            -- Usage tracking
            created_at TIMESTAMP DEFAULT NOW(),
            last_used_at TIMESTAMP DEFAULT NOW(),
            usage_count INTEGER DEFAULT 1
        );
    """,

    'translation_cache_indexes': """
        CREATE INDEX IF NOT EXISTS idx_hash_lookup ON translation_cache(source_text_hash);
        CREATE INDEX IF NOT EXISTS idx_usage ON translation_cache(last_used_at, usage_count);
        CREATE INDEX IF NOT EXISTS idx_language_pair ON translation_cache(source_language, target_language);
    """,

    'scrape_progress': """
        CREATE TABLE IF NOT EXISTS scrape_progress (
            id BIGSERIAL PRIMARY KEY,
            source_site TEXT NOT NULL UNIQUE,
            last_success_page INTEGER NOT NULL DEFAULT 0,
            last_success_at TIMESTAMP DEFAULT NOW(),
            last_session_id TEXT
        );
    """,

    'scrape_progress_indexes': """
        CREATE INDEX IF NOT EXISTS idx_scrape_progress_site ON scrape_progress(source_site);
    """
}

# Define table creation order (for foreign key dependencies)
TABLE_ORDER = [
    'raw_scrapes', 'raw_scrapes_indexes',
    'locations', 'locations_indexes',
    'skills', 'skills_indexes',
    'companies', 'companies_indexes',
    'job_postings', 'job_postings_indexes',
    'job_discoveries', 'job_discoveries_indexes',
    'job_tracking', 'job_tracking_indexes',
    'job_skills', 'job_skills_indexes',
    'company_tracking', 'company_tracking_indexes',
    'processing_logs', 'processing_logs_indexes',
    'translation_cache', 'translation_cache_indexes',
    'scrape_progress', 'scrape_progress_indexes'
]
