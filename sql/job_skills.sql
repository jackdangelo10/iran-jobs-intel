CREATE TABLE job_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    job_posting_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    
    -- Requirement details
    requirement_type TEXT CHECK (requirement_type IN ('required', 'preferred', 'nice_to_have', 'mentioned')) NOT NULL,
    proficiency_level TEXT CHECK (proficiency_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',
    years_experience INTEGER,
    
    -- Extraction context
    mention_context TEXT,                    -- Where/how it was mentioned in job posting
    confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    extraction_method TEXT CHECK (extraction_method IN ('keyword_match', 'nlp_extraction', 'manual_review')) DEFAULT 'keyword_match',
    
    -- Processing
    verified BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_posting_id) REFERENCES job_postings(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    
    UNIQUE(job_posting_id, skill_id),
    
    CREATE INDEX idx_job ON job_skills(job_posting_id);
    CREATE INDEX idx_skill ON job_skills(skill_id);
    CREATE INDEX idx_requirement_type ON job_skills(requirement_type);
    CREATE INDEX idx_confidence ON job_skills(confidence_score);
);