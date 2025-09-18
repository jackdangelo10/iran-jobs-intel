CREATE TABLE translation_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Source content
    source_text_hash TEXT UNIQUE NOT NULL,  -- SHA-256 hash of source text
    source_text TEXT NOT NULL,
    source_language TEXT DEFAULT 'fa',
    target_language TEXT DEFAULT 'en',
    
    -- Translation result
    translated_text TEXT,
    translation_service TEXT DEFAULT 'google',
    translation_confidence REAL,
    
    -- Usage tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 1,
    
    -- Quality tracking
    is_verified BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    
    CREATE INDEX idx_hash_lookup ON translation_cache(source_text_hash);
    CREATE INDEX idx_usage ON translation_cache(last_used_at, usage_count);
    CREATE INDEX idx_language_pair ON translation_cache(source_language, target_language);
);