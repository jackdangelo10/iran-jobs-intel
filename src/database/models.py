# src/database/models.py
"""
Pydantic models for database entities.
Provides type safety and validation for data flowing through the system.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from datetime import date, datetime
from typing import Any


class RawScrape(BaseModel):
    """Model for raw scrape data."""
    
    # Required fields
    source_site: str = Field(..., pattern="^(irantalent|jobvision|jobinja)$")
    source_url: str
    page_type: str = Field(..., pattern="^(job_list|job_detail|company_profile)$")
    scrape_session_id: str
    raw_html: str
    response_status: int = 200
    
    # Optional fields
    id: int | None = None
    html_size: int | None = None
    content_hash: str | None = None
    is_duplicate: bool = False
    processing_status: str = "pending"
    error_message: str | None = None
    scraped_at: datetime | None = None
    
    class Config:
        from_attributes = True  # Allows creating from ORM objects


class JobDiscovery(BaseModel):
    """Model for discovered job URLs during scraping."""
    
    # Required fields
    scrape_session_id: str
    job_url: str
    source_site: str = Field(..., pattern="^(irantalent|jobvision|jobinja)$")
    
    # Optional fields
    id: int | None = None
    company_url: str | None = None
    found_on_page: str | None = None
    discovered_at: datetime | None = None
    
    class Config:
        from_attributes = True


class JobTracking(BaseModel):
    """Model for job URL lifecycle tracking."""
    
    # Required fields
    job_url: str
    source_site: str = Field(..., pattern="^(irantalent|jobvision|jobinja)$")
    first_seen_session: str
    last_seen_session: str
    first_seen_date: date
    last_seen_date: date
    
    # Optional fields
    id: int | None = None
    is_active: bool = True
    disappeared_date: date | None = None
    disappeared_session: str | None = None
    detail_scraped: bool = False
    last_detail_scrape_date: date | None = None
    detail_scrape_count: int = 0
    
    class Config:
        from_attributes = True


class JobPosting(BaseModel):
    """Model for job posting data."""
    
    # Required fields
    source_site: str = Field(..., pattern="^(irantalent|jobvision|jobinja)$")
    source_url: str
    title_persian: str
    first_seen_date: date
    last_seen_date: date
    
    # Optional fields - Source tracking
    id: int | None = None
    raw_scrape_id: int | None = None
    external_id: str | None = None
    
    # Optional fields - Content
    title_english: str | None = None
    title_normalized: str | None = None
    description_persian: str | None = None
    description_english: str | None = None
    description_summary: str | None = None
    
    # Optional fields - Company
    company_name_raw: str | None = None
    company_url: str | None = None
    company_id: int | None = None
    
    # Optional fields - Location
    location_raw: str | None = None
    location_id: int | None = None
    is_remote: bool = False
    
    # Optional fields - Employment details
    employment_type: str = "unknown"
    experience_level: str = "unknown"
    experience_years_min: int | None = None
    experience_years_max: int | None = None
    
    # Optional fields - Demographics
    gender_requirement: str = "unknown"
    
    # Optional fields - Education
    education_level: str = "unknown"
    education_field: str | None = None
    
    # Optional fields - Salary
    salary_min_original: float | None = None
    salary_max_original: float | None = None
    salary_currency_original: str = "IRR"
    salary_period: str = "unknown"
    salary_min_irr: float | None = None
    salary_max_irr: float | None = None
    salary_min_usd: float | None = None
    salary_max_usd: float | None = None
    exchange_rate_used: float | None = None
    exchange_rate_date: date | None = None
    
    # Optional fields - Skills (as Python lists, will be JSON in DB)
    skills_required: list[str] | None = None
    skills_preferred: list[str] | None = None
    technologies_mentioned: list[str] | None = None
    
    # Optional fields - Processing metadata
    data_quality_score: float | None = Field(None, ge=0, le=1)
    processing_confidence: float | None = Field(None, ge=0, le=1)
    manual_review_needed: bool = False
    
    # Optional fields - Temporal
    posted_date: date | None = None
    application_deadline: date | None = None
    is_active: bool = True
    deactivated_date: date | None = None
    processing_status: str = "pending"
    
    class Config:
        from_attributes = True
    
    def to_db_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for database insertion.
        Handles JSON serialization for list fields.
        """
        import json
        
        data = self.model_dump(exclude_none=True, exclude={'id'})
        
        # Convert list fields to JSON strings for database
        if 'skills_required' in data and data['skills_required']:
            data['skills_required_json'] = json.dumps(data.pop('skills_required'))
        if 'skills_preferred' in data and data['skills_preferred']:
            data['skills_preferred_json'] = json.dumps(data.pop('skills_preferred'))
        if 'technologies_mentioned' in data and data['technologies_mentioned']:
            data['technologies_mentioned_json'] = json.dumps(data.pop('technologies_mentioned'))
        
        return data


class CompanyTracking(BaseModel):
    """Model for company URL tracking."""
    
    # Required fields
    company_url: str
    source_site: str = Field(..., pattern="^(irantalent|jobvision|jobinja)$")
    first_seen_session: str
    last_seen_session: str
    first_seen_date: date
    last_seen_date: date
    
    # Optional fields
    id: int | None = None
    profile_scraped: bool = False
    last_profile_scrape_date: date | None = None
    profile_scrape_count: int = 0
    
    class Config:
        from_attributes = True


class Company(BaseModel):
    """Model for company data."""
    
    # Required fields
    first_seen_date: date
    
    # Optional fields - Basic info
    id: int | None = None
    display_name_persian: str | None = None
    display_name_english: str | None = None
    canonical_name: str | None = None
    name_variations: list[str] | None = None
    
    # Optional fields - Identification
    company_registration_number: str | None = None
    tax_id: str | None = None
    website_url: str | None = None
    linkedin_url: str | None = None
    
    # Optional fields - Classification
    company_type: str = "unknown"
    parent_company_id: int | None = None
    
    # Optional fields - Industry
    primary_sector: str | None = None
    secondary_sectors: list[str] | None = None
    business_description_persian: str | None = None
    business_description_english: str | None = None
    
    # Optional fields - Size
    employee_count_estimate: int | None = None
    employee_size_category: str = "unknown"
    annual_revenue_estimate: float | None = None
    
    # Optional fields - Geographic
    headquarters_location_id: int | None = None
    locations: list[int] | None = None
    
    # Optional fields - Risk
    is_sanctioned: bool = False
    sanction_programs: list[str] | None = None
    risk_level: str = "unknown"
    compliance_notes: str | None = None
    
    # Optional fields - Network
    connected_entities: dict[str, Any] | None = None
    government_contracts: bool = False
    defense_related: bool = False
    
    # Optional fields - Lifecycle
    founded_year: int | None = None
    last_activity_date: date | None = None
    is_active: bool = True
    
    # Optional fields - Hiring metrics
    total_job_postings: int = 0
    active_job_postings: int = 0
    avg_posting_frequency: float | None = None
    hiring_velocity_30d: float | None = None
    
    # Optional fields - Processing
    profile_completeness_score: float | None = Field(None, ge=0, le=1)
    needs_manual_review: bool = False
    
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    class Config:
        from_attributes = True