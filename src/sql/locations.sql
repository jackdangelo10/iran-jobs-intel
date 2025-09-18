CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Iranian administrative hierarchy
    country TEXT DEFAULT 'Iran',
    province_persian TEXT,           -- استان تهران
    province_english TEXT,           -- Tehran Province  
    city_persian TEXT,               -- تهران
    city_english TEXT,               -- Tehran
    district_persian TEXT,           -- منطقه ۱
    district_english TEXT,           -- District 1
    
    -- Standardized location (for matching/deduplication)
    location_normalized TEXT UNIQUE, -- "tehran-tehran-district1"
    location_type TEXT CHECK (location_type IN ('country', 'province', 'city', 'district', 'industrial_zone', 'free_trade_zone')),
    
    -- Geographic coordinates
    latitude REAL,
    longitude REAL,
    
    -- Economic classification (static)
    economic_zone_type TEXT CHECK (economic_zone_type IN ('regular', 'special_economic_zone', 'free_trade_zone', 'industrial_park', 'unknown')) DEFAULT 'regular',
    development_level TEXT CHECK (development_level IN ('developed', 'developing', 'underdeveloped', 'unknown')) DEFAULT 'unknown',
    
    -- Administrative codes
    iso_province_code TEXT,          -- ISO 3166-2 codes for Iranian provinces
    postal_code_prefix TEXT,
    
    -- Processing (static)
    location_variations_json TEXT,   -- All name variations we've seen
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CREATE INDEX idx_normalized ON locations(location_normalized);
    CREATE INDEX idx_province ON locations(province_english);
    CREATE INDEX idx_city ON locations(city_english);
    CREATE INDEX idx_coordinates ON locations(latitude, longitude);
);