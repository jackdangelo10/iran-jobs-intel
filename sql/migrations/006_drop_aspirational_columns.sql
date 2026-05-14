-- Migration 006: Drop aspirational columns + unused company_locations table.
--
-- Background: the schema was originally written with many columns that no
-- pipeline code ever populates (sanctions flags, salary USD conversions,
-- coordinate fields, etc.). This migration drops them so the schema matches
-- what the code actually reads or writes.
--
-- This is DESTRUCTIVE: any data in the dropped columns is lost. The columns
-- being dropped here are either always NULL (never written) or only ever
-- held heuristic values (data_quality_score / processing_confidence) that
-- were not surfaced anywhere.
--
-- Run this as the database owner in Supabase SQL Editor.

BEGIN;

-- ----------------------------------------------------------------------------
-- job_postings: drop unused / heuristic columns
-- ----------------------------------------------------------------------------
ALTER TABLE job_postings
    DROP COLUMN IF EXISTS description_summary,
    DROP COLUMN IF EXISTS experience_years_min,
    DROP COLUMN IF EXISTS experience_years_max,
    DROP COLUMN IF EXISTS education_field,
    DROP COLUMN IF EXISTS is_remote,
    DROP COLUMN IF EXISTS salary_period,
    DROP COLUMN IF EXISTS salary_min_irr,
    DROP COLUMN IF EXISTS salary_max_irr,
    DROP COLUMN IF EXISTS salary_min_usd,
    DROP COLUMN IF EXISTS salary_max_usd,
    DROP COLUMN IF EXISTS exchange_rate_used,
    DROP COLUMN IF EXISTS exchange_rate_date,
    DROP COLUMN IF EXISTS application_deadline,
    DROP COLUMN IF EXISTS data_quality_score,
    DROP COLUMN IF EXISTS processing_confidence,
    DROP COLUMN IF EXISTS manual_review_needed;

DROP INDEX IF EXISTS idx_gender_requirement;

-- ----------------------------------------------------------------------------
-- companies: drop all the aspirational fields (sanctions, classification, etc.)
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_company_type;
DROP INDEX IF EXISTS idx_risk_level;
DROP INDEX IF EXISTS idx_sanctioned;

ALTER TABLE companies
    DROP COLUMN IF EXISTS display_name_english,
    DROP COLUMN IF EXISTS name_variations_json,
    DROP COLUMN IF EXISTS company_registration_number,
    DROP COLUMN IF EXISTS tax_id,
    DROP COLUMN IF EXISTS website_url,
    DROP COLUMN IF EXISTS linkedin_url,
    DROP COLUMN IF EXISTS company_type,
    DROP COLUMN IF EXISTS parent_company_id,
    DROP COLUMN IF EXISTS primary_sector,
    DROP COLUMN IF EXISTS secondary_sectors_json,
    DROP COLUMN IF EXISTS business_description_persian,
    DROP COLUMN IF EXISTS business_description_english,
    DROP COLUMN IF EXISTS employee_count_estimate,
    DROP COLUMN IF EXISTS employee_size_category,
    DROP COLUMN IF EXISTS annual_revenue_estimate,
    DROP COLUMN IF EXISTS headquarters_location_id,
    DROP COLUMN IF EXISTS locations_json,
    DROP COLUMN IF EXISTS is_sanctioned,
    DROP COLUMN IF EXISTS sanction_programs_json,
    DROP COLUMN IF EXISTS risk_level,
    DROP COLUMN IF EXISTS compliance_notes,
    DROP COLUMN IF EXISTS connected_entities_json,
    DROP COLUMN IF EXISTS government_contracts,
    DROP COLUMN IF EXISTS defense_related,
    DROP COLUMN IF EXISTS founded_year,
    DROP COLUMN IF EXISTS avg_posting_frequency,
    DROP COLUMN IF EXISTS profile_completeness_score,
    DROP COLUMN IF EXISTS needs_manual_review;

-- ----------------------------------------------------------------------------
-- locations: drop coordinates, province/district fields, economic zone, etc.
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_province;
DROP INDEX IF EXISTS idx_city;
DROP INDEX IF EXISTS idx_coordinates;

ALTER TABLE locations
    DROP COLUMN IF EXISTS country,
    DROP COLUMN IF EXISTS province_persian,
    DROP COLUMN IF EXISTS province_english,
    DROP COLUMN IF EXISTS city_english,
    DROP COLUMN IF EXISTS district_persian,
    DROP COLUMN IF EXISTS district_english,
    DROP COLUMN IF EXISTS latitude,
    DROP COLUMN IF EXISTS longitude,
    DROP COLUMN IF EXISTS economic_zone_type,
    DROP COLUMN IF EXISTS development_level,
    DROP COLUMN IF EXISTS iso_province_code,
    DROP COLUMN IF EXISTS postal_code_prefix,
    DROP COLUMN IF EXISTS location_variations_json;

-- ----------------------------------------------------------------------------
-- skills: keep only english name + category + lifecycle
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_category;
DROP INDEX IF EXISTS idx_dual_use;
DROP INDEX IF EXISTS idx_active;  -- legacy duplicate name; new index is idx_skill_active

-- Drop self-FK before dropping parent_skill_id
ALTER TABLE skills
    DROP CONSTRAINT IF EXISTS skills_parent_skill_id_fkey;

ALTER TABLE skills
    DROP COLUMN IF EXISTS skill_name_persian,
    DROP COLUMN IF EXISTS skill_aliases_json,
    DROP COLUMN IF EXISTS skill_subcategory,
    DROP COLUMN IF EXISTS technology_domain,
    DROP COLUMN IF EXISTS skill_level,
    DROP COLUMN IF EXISTS learning_curve,
    DROP COLUMN IF EXISTS is_dual_use,
    DROP COLUMN IF EXISTS export_control_classification,
    DROP COLUMN IF EXISTS strategic_importance,
    DROP COLUMN IF EXISTS primary_industries_json,
    DROP COLUMN IF EXISTS skill_description,
    DROP COLUMN IF EXISTS parent_skill_id,
    DROP COLUMN IF EXISTS related_skills_json,
    DROP COLUMN IF EXISTS prerequisite_skills_json,
    DROP COLUMN IF EXISTS confidence_score,
    DROP COLUMN IF EXISTS needs_verification;

-- Expand skill_category to include 'database' and 'cloud'
ALTER TABLE skills
    DROP CONSTRAINT IF EXISTS skills_skill_category_check;
ALTER TABLE skills
    ADD CONSTRAINT skills_skill_category_check CHECK (skill_category IN (
        'language', 'framework', 'database', 'cloud',
        'tool', 'methodology', 'soft', 'certification', 'domain_knowledge'
    ));

CREATE INDEX IF NOT EXISTS idx_skill_category ON skills(skill_category);
CREATE INDEX IF NOT EXISTS idx_skill_active ON skills(is_active);

-- ----------------------------------------------------------------------------
-- job_skills: drop never-populated extraction context columns
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_confidence;

ALTER TABLE job_skills
    DROP COLUMN IF EXISTS years_experience,
    DROP COLUMN IF EXISTS mention_context,
    DROP COLUMN IF EXISTS verified,
    DROP COLUMN IF EXISTS needs_review;

-- ----------------------------------------------------------------------------
-- processing_logs: drop never-populated columns
-- ----------------------------------------------------------------------------
ALTER TABLE processing_logs
    DROP COLUMN IF EXISTS processing_time_ms,
    DROP COLUMN IF EXISTS error_code,
    DROP COLUMN IF EXISTS stack_trace;

-- ----------------------------------------------------------------------------
-- translation_cache: drop unused review flags
-- ----------------------------------------------------------------------------
ALTER TABLE translation_cache
    DROP COLUMN IF EXISTS is_verified,
    DROP COLUMN IF EXISTS needs_review;

-- ----------------------------------------------------------------------------
-- company_locations: nothing writes to this table; drop it entirely
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS company_locations;

COMMIT;
