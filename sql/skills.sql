CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Skill identification
    skill_name_english TEXT UNIQUE NOT NULL,  -- "Python", "Machine Learning"
    skill_name_persian TEXT,                  -- "پایتون", "یادگیری ماشین"
    skill_aliases_json TEXT,                  -- ["Python 3", "Python3", "پایتون ۳"]
    
    -- Classification
    skill_category TEXT CHECK (skill_category IN ('technical', 'soft', 'language', 'certification', 'tool', 'framework', 'methodology', 'domain_knowledge')) NOT NULL,
    skill_subcategory TEXT,                   -- "programming_language", "database", "cloud_platform"
    technology_domain TEXT,                   -- "software", "hardware", "data_science", "devops"
    
    -- Skill characteristics
    skill_level TEXT CHECK (skill_level IN ('basic', 'intermediate', 'advanced', 'expert', 'unknown')) DEFAULT 'unknown',
    learning_curve TEXT CHECK (learning_curve IN ('easy', 'medium', 'hard', 'very_hard', 'unknown')) DEFAULT 'unknown',
    
    -- Dual-use and compliance (from your original spec)
    is_dual_use BOOLEAN DEFAULT FALSE,
    export_control_classification TEXT,        -- ECCN codes if applicable
    strategic_importance TEXT CHECK (strategic_importance IN ('low', 'medium', 'high', 'critical', 'unknown')) DEFAULT 'low',
    
    -- Industry relevance
    primary_industries_json TEXT,             -- ["software", "finance", "defense"]
    skill_description TEXT,                   -- What this skill actually is
    
    -- Skill relationships
    parent_skill_id INTEGER,                  -- "React" -> parent: "JavaScript"
    related_skills_json TEXT,                 -- Skills that often appear together
    prerequisite_skills_json TEXT,            -- Skills needed before this one
    
    -- Processing metadata
    confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 1.0,
    needs_verification BOOLEAN DEFAULT FALSE,
    
    -- Lifecycle
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,           -- Still relevant/in use
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_skill_id) REFERENCES skills(id),
    
    CREATE INDEX idx_skill_name ON skills(skill_name_english);
    CREATE INDEX idx_category ON skills(skill_category, skill_subcategory);
    CREATE INDEX idx_dual_use ON skills(is_dual_use, strategic_importance);
    CREATE INDEX idx_active ON skills(is_active);
);