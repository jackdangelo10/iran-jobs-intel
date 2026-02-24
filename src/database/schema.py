# src/database/schema.py
"""
PostgreSQL database schema for Iran Jobs Intelligence Platform.
All tables are created in the 'iran_jobs' schema.
"""

# Schema creation - must be first
SCHEMA_CREATION = """
CREATE SCHEMA IF NOT EXISTS iran_jobs;
"""

SCHEMA_SQL = {
    'schema_setup': SCHEMA_CREATION,
    
    'raw_scrapes': """
        CREATE TABLE IF NOT EXISTS iran_jobs.raw_scrapes (
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
        CREATE INDEX IF NOT EXISTS idx_scrape_session ON iran_jobs.raw_scrapes(scrape_session_id);
        CREATE INDEX IF NOT EXISTS idx_processing_status ON iran_jobs.raw_scrapes(processing_status);
        CREATE INDEX IF NOT EXISTS idx_scraped_date ON iran_jobs.raw_scrapes(scraped_at);
        CREATE INDEX IF NOT EXISTS idx_content_hash ON iran_jobs.raw_scrapes(content_hash);
    """,
    
    'locations': """
        CREATE TABLE IF NOT EXISTS iran_jobs.locations (
            id SERIAL PRIMARY KEY,
            
            -- Iranian administrative hierarchy
            country TEXT DEFAULT 'Iran',
            province_persian TEXT,
            province_english TEXT,
            city_persian TEXT,
            city_english TEXT,
            district_persian TEXT,
            district_english TEXT,
            
            -- Standardized location
            location_normalized TEXT UNIQUE,
            location_type TEXT CHECK (location_type IN ('country', 'province', 'city', 'district', 'industrial_zone', 'free_trade_zone')),
            
            -- Geographic coordinates
            latitude NUMERIC,
            longitude NUMERIC,
            
            -- Economic classification
            economic_zone_type TEXT CHECK (economic_zone_type IN ('regular', 'special_economic_zone', 'free_trade_zone', 'industrial_park', 'unknown')) DEFAULT 'regular',
            development_level TEXT CHECK (development_level IN ('developed', 'developing', 'underdeveloped', 'unknown')) DEFAULT 'unknown',
            
            -- Administrative codes
            iso_province_code TEXT,
            postal_code_prefix TEXT,
            
            -- Processing
            location_variations_json JSONB,
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """,
    
    'locations_indexes': """
        CREATE INDEX IF NOT EXISTS idx_normalized ON iran_jobs.locations(location_normalized);
        CREATE INDEX IF NOT EXISTS idx_province ON iran_jobs.locations(province_english);
        CREATE INDEX IF NOT EXISTS idx_city ON iran_jobs.locations(city_english);
        CREATE INDEX IF NOT EXISTS idx_coordinates ON iran_jobs.locations(latitude, longitude);
    """,
    
    'skills': """
        CREATE TABLE IF NOT EXISTS iran_jobs.skills (
            id SERIAL PRIMARY KEY,
            
            -- Skill identification
            skill_name_english TEXT UNIQUE NOT NULL,
            skill_name_persian TEXT,
            skill_aliases_json JSONB,
            
            -- Classification
            skill_category TEXT CHECK (skill_category IN ('technical', 'soft', 'language', 'certification', 'tool', 'framework', 'methodology', 'domain_knowledge')) NOT NULL,
            skill_subcategory TEXT,
            technology_domain TEXT,
            
            -- Skill characteristics
            skill_level TEXT CHECK (skill_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',
            learning_curve TEXT CHECK (learning_curve IN ('easy', 'medium', 'hard', 'very_hard', 'unknown')) DEFAULT 'unknown',
            
            -- Dual-use and compliance
            is_dual_use BOOLEAN DEFAULT FALSE,
            export_control_classification TEXT,
            strategic_importance TEXT CHECK (strategic_importance IN ('low', 'medium', 'high', 'critical', 'unknown')) DEFAULT 'low',
            
            -- Industry relevance
            primary_industries_json JSONB,
            skill_description TEXT,
            
            -- Skill relationships
            parent_skill_id INTEGER,
            related_skills_json JSONB,
            prerequisite_skills_json JSONB,
            
            -- Processing metadata
            confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
            needs_verification BOOLEAN DEFAULT FALSE,
            
            -- Lifecycle
            first_seen_date DATE NOT NULL,
            last_seen_date DATE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            
            FOREIGN KEY (parent_skill_id) REFERENCES iran_jobs.skills(id)
        );
    """,
    
    'skills_indexes': """
        CREATE INDEX IF NOT EXISTS idx_skill_name ON iran_jobs.skills(skill_name_english);
        CREATE INDEX IF NOT EXISTS idx_category ON iran_jobs.skills(skill_category, skill_subcategory);
        CREATE INDEX IF NOT EXISTS idx_dual_use ON iran_jobs.skills(is_dual_use, strategic_importance);
        CREATE INDEX IF NOT EXISTS idx_active ON iran_jobs.skills(is_active);
    """,
    
    'companies': """
        CREATE TABLE IF NOT EXISTS iran_jobs.companies (
            id SERIAL PRIMARY KEY,
            
            -- Basic company information
            display_name_persian TEXT,
            display_name_english TEXT,
            canonical_name TEXT UNIQUE,
            name_variations_json JSONB,
            
            -- Company identification
            company_registration_number TEXT,
            tax_id TEXT,
            website_url TEXT,
            linkedin_url TEXT,
            
            -- Classification
            company_type TEXT CHECK (company_type IN ('private', 'state_owned', 'semi_state', 'irgc_linked', 'foundation', 'cooperative', 'foreign', 'unknown')) DEFAULT 'unknown',
            parent_company_id INTEGER,
            
            -- Industry classification
            primary_sector TEXT,
            secondary_sectors_json JSONB,
            business_description_persian TEXT,
            business_description_english TEXT,
            
            -- Size indicators
            employee_count_estimate INTEGER,
            employee_size_category TEXT CHECK (employee_size_category IN ('startup', 'small', 'medium', 'large', 'enterprise', 'unknown')) DEFAULT 'unknown',
            annual_revenue_estimate NUMERIC,
            
            -- Geographic presence
            headquarters_location_id INTEGER,
            locations_json JSONB,
            
            -- Risk and compliance
            is_sanctioned BOOLEAN DEFAULT FALSE,
            sanction_programs_json JSONB,
            risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'critical', 'unknown')) DEFAULT 'unknown',
            compliance_notes TEXT,
            
            -- Network analysis
            connected_entities_json JSONB,
            government_contracts BOOLEAN DEFAULT FALSE,
            defense_related BOOLEAN DEFAULT FALSE,
            
            -- Company lifecycle
            founded_year INTEGER,
            first_seen_date DATE NOT NULL,
            last_activity_date DATE,
            is_active BOOLEAN DEFAULT TRUE,
            
            -- Hiring metrics
            total_job_postings INTEGER DEFAULT 0,
            active_job_postings INTEGER DEFAULT 0,
            avg_posting_frequency NUMERIC,
            hiring_velocity_30d NUMERIC,
            
            -- Processing status
            profile_completeness_score NUMERIC CHECK (profile_completeness_score >= 0 AND profile_completeness_score <= 1),
            needs_manual_review BOOLEAN DEFAULT FALSE,
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            
            FOREIGN KEY (parent_company_id) REFERENCES iran_jobs.companies(id),
            FOREIGN KEY (headquarters_location_id) REFERENCES iran_jobs.locations(id)
        );
    """,
    
    'companies_indexes': """
        CREATE INDEX IF NOT EXISTS idx_canonical_name ON iran_jobs.companies(canonical_name);
        CREATE INDEX IF NOT EXISTS idx_company_type ON iran_jobs.companies(company_type);
        CREATE INDEX IF NOT EXISTS idx_risk_level ON iran_jobs.companies(risk_level);
        CREATE INDEX IF NOT EXISTS idx_sanctioned ON iran_jobs.companies(is_sanctioned);
        CREATE INDEX IF NOT EXISTS idx_active ON iran_jobs.companies(is_active);
        CREATE INDEX IF NOT EXISTS idx_hiring_activity ON iran_jobs.companies(active_job_postings);
    """,
    
    'job_postings': """
        CREATE TABLE IF NOT EXISTS iran_jobs.job_postings (
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
            description_summary TEXT,
            
            -- Company information
            company_name_raw TEXT,
            company_url TEXT,
            company_id INTEGER,
            
            -- Location
            location_raw TEXT,
            location_id INTEGER,
            is_remote BOOLEAN DEFAULT FALSE,
            
            -- Employment details
            employment_type TEXT DEFAULT 'unknown',
            experience_level TEXT DEFAULT 'unknown',
            experience_years_min INTEGER,
            experience_years_max INTEGER,

            -- Demographics
            gender_requirement TEXT DEFAULT 'unknown',
        
            
            -- Education requirements
            education_level TEXT DEFAULT 'unknown',
            education_field TEXT,
            
            -- Salary
            salary_min_original NUMERIC,
            salary_max_original NUMERIC,
            salary_currency_original TEXT DEFAULT 'IRR',
            salary_period TEXT DEFAULT 'unknown',
            
            -- Converted salaries
            salary_min_irr NUMERIC,
            salary_max_irr NUMERIC,
            salary_min_usd NUMERIC,
            salary_max_usd NUMERIC,
            exchange_rate_used NUMERIC,
            exchange_rate_date DATE,
            
            -- Skills
            skills_required_json JSONB,
            skills_preferred_json JSONB,
            technologies_mentioned_json JSONB,
            
            -- Processing metadata
            data_quality_score NUMERIC CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
            processing_confidence NUMERIC CHECK (processing_confidence >= 0 AND processing_confidence <= 1),
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
            
            FOREIGN KEY (raw_scrape_id) REFERENCES iran_jobs.raw_scrapes(id),
            FOREIGN KEY (company_id) REFERENCES iran_jobs.companies(id),
            FOREIGN KEY (location_id) REFERENCES iran_jobs.locations(id),
            
            UNIQUE(source_site, external_id)
        );
    """,
    
    'job_postings_indexes': """
        CREATE INDEX IF NOT EXISTS idx_company_name ON iran_jobs.job_postings(company_name_raw);
        CREATE INDEX IF NOT EXISTS idx_posted_date ON iran_jobs.job_postings(posted_date);
        CREATE INDEX IF NOT EXISTS idx_active ON iran_jobs.job_postings(is_active);
        CREATE INDEX IF NOT EXISTS idx_processing_status ON iran_jobs.job_postings(processing_status);
        CREATE INDEX IF NOT EXISTS idx_employment_type ON iran_jobs.job_postings(employment_type);
        CREATE INDEX IF NOT EXISTS idx_experience_level ON iran_jobs.job_postings(experience_level);
        CREATE INDEX IF NOT EXISTS idx_gender_requirement ON iran_jobs.job_postings(gender_requirement);  
    """,
    
    'job_discoveries': """
        CREATE TABLE IF NOT EXISTS iran_jobs.job_discoveries (
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
        CREATE INDEX IF NOT EXISTS idx_session ON iran_jobs.job_discoveries(scrape_session_id);
        CREATE INDEX IF NOT EXISTS idx_job_url ON iran_jobs.job_discoveries(job_url);
    """,
    
    'job_tracking': """
        CREATE TABLE IF NOT EXISTS iran_jobs.job_tracking (
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
        CREATE INDEX IF NOT EXISTS idx_job_url ON iran_jobs.job_tracking(job_url);
        CREATE INDEX IF NOT EXISTS idx_active ON iran_jobs.job_tracking(is_active);
        CREATE INDEX IF NOT EXISTS idx_last_seen ON iran_jobs.job_tracking(last_seen_date);
    """,
    
    'job_skills': """
        CREATE TABLE IF NOT EXISTS iran_jobs.job_skills (
            id BIGSERIAL PRIMARY KEY,
            
            job_posting_id BIGINT NOT NULL,
            skill_id INTEGER NOT NULL,
            
            -- Requirement details
            requirement_type TEXT CHECK (requirement_type IN ('required', 'preferred', 'nice_to_have', 'mentioned')) NOT NULL,
            proficiency_level TEXT CHECK (proficiency_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',
            years_experience INTEGER,
            
            -- Extraction context
            mention_context TEXT,
            confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
            extraction_method TEXT CHECK (extraction_method IN ('keyword_match', 'nlp_extraction', 'manual_review')) DEFAULT 'keyword_match',
            
            -- Processing
            verified BOOLEAN DEFAULT FALSE,
            needs_review BOOLEAN DEFAULT FALSE,
            
            created_at TIMESTAMP DEFAULT NOW(),
            
            FOREIGN KEY (job_posting_id) REFERENCES iran_jobs.job_postings(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES iran_jobs.skills(id),
            
            UNIQUE(job_posting_id, skill_id)
        );
    """,
    
    'job_skills_indexes': """
        CREATE INDEX IF NOT EXISTS idx_job ON iran_jobs.job_skills(job_posting_id);
        CREATE INDEX IF NOT EXISTS idx_skill ON iran_jobs.job_skills(skill_id);
        CREATE INDEX IF NOT EXISTS idx_requirement_type ON iran_jobs.job_skills(requirement_type);
        CREATE INDEX IF NOT EXISTS idx_confidence ON iran_jobs.job_skills(confidence_score);
    """,
    
    'company_locations': """
        CREATE TABLE IF NOT EXISTS iran_jobs.company_locations (
            id SERIAL PRIMARY KEY,
            
            company_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            
            -- Relationship type
            location_type TEXT CHECK (location_type IN ('headquarters', 'office', 'branch', 'remote_hub', 'subsidiary', 'unknown')) NOT NULL,
            
            -- Details
            office_name TEXT,
            employee_count_estimate INTEGER,
            is_primary BOOLEAN DEFAULT FALSE,
            
            -- Address details
            address_persian TEXT,
            address_english TEXT,
            
            -- Operational status
            is_active BOOLEAN DEFAULT TRUE,
            established_date DATE,
            closed_date DATE,
            
            -- Processing
            confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
            
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            
            FOREIGN KEY (company_id) REFERENCES iran_jobs.companies(id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES iran_jobs.locations(id),
            
            UNIQUE(company_id, location_id, location_type)
        );
    """,
    
    'company_locations_indexes': """
        CREATE INDEX IF NOT EXISTS idx_company ON iran_jobs.company_locations(company_id);
        CREATE INDEX IF NOT EXISTS idx_location ON iran_jobs.company_locations(location_id);
        CREATE INDEX IF NOT EXISTS idx_primary ON iran_jobs.company_locations(is_primary);
        CREATE INDEX IF NOT EXISTS idx_active ON iran_jobs.company_locations(is_active);
    """,
    
    'company_tracking': """
        CREATE TABLE IF NOT EXISTS iran_jobs.company_tracking (
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
        CREATE INDEX IF NOT EXISTS idx_company_url ON iran_jobs.company_tracking(company_url);
        CREATE INDEX IF NOT EXISTS idx_last_seen ON iran_jobs.company_tracking(last_seen_date);
    """,
    
    'processing_logs': """
        CREATE TABLE IF NOT EXISTS iran_jobs.processing_logs (
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
            processing_time_ms INTEGER,
            records_processed INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,
            
            -- Error details
            error_code TEXT,
            error_details TEXT,
            stack_trace TEXT,
            
            timestamp TIMESTAMP DEFAULT NOW()
        );
    """,
    
    'processing_logs_indexes': """
        CREATE INDEX IF NOT EXISTS idx_process_type ON iran_jobs.processing_logs(process_type, status);
        CREATE INDEX IF NOT EXISTS idx_session ON iran_jobs.processing_logs(scrape_session_id);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON iran_jobs.processing_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_entity ON iran_jobs.processing_logs(entity_type, entity_id);
    """,
    
    'translation_cache': """
        CREATE TABLE IF NOT EXISTS iran_jobs.translation_cache (
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
            usage_count INTEGER DEFAULT 1,
            
            -- Quality tracking
            is_verified BOOLEAN DEFAULT FALSE,
            needs_review BOOLEAN DEFAULT FALSE
        );
    """,
    
    'translation_cache_indexes': """
        CREATE INDEX IF NOT EXISTS idx_hash_lookup ON iran_jobs.translation_cache(source_text_hash);
        CREATE INDEX IF NOT EXISTS idx_usage ON iran_jobs.translation_cache(last_used_at, usage_count);
        CREATE INDEX IF NOT EXISTS idx_language_pair ON iran_jobs.translation_cache(source_language, target_language);
    """
}

# Define table creation order (for foreign key dependencies)
TABLE_ORDER = [
    'schema_setup',  # Create schema first
    'raw_scrapes', 'raw_scrapes_indexes',
    'locations', 'locations_indexes', 
    'skills', 'skills_indexes',
    'companies', 'companies_indexes',
    'job_postings', 'job_postings_indexes',
    'job_discoveries', 'job_discoveries_indexes',
    'job_tracking', 'job_tracking_indexes',
    'job_skills', 'job_skills_indexes',
    'company_locations', 'company_locations_indexes', 
    'company_tracking', 'company_tracking_indexes',
    'processing_logs', 'processing_logs_indexes',
    'translation_cache', 'translation_cache_indexes'
]
