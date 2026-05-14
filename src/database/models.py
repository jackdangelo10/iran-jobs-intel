# src/database/models.py
"""
Pydantic models for database entities.
Provides type safety and validation for data flowing through the system.

Trimmed to match the schema after migration 006 — only columns the pipeline
actually populates.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
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
        from_attributes = True


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

    # Source tracking
    id: int | None = None
    raw_scrape_id: int | None = None
    external_id: str | None = None

    # Content
    title_english: str | None = None
    title_normalized: str | None = None
    description_persian: str | None = None
    description_english: str | None = None

    # Company
    company_name_raw: str | None = None
    company_url: str | None = None
    company_id: int | None = None

    # Location
    location_raw: str | None = None
    location_id: int | None = None

    # Employment details
    employment_type: str = "unknown"
    experience_level: str = "unknown"

    # Demographics (scraped but not yet surfaced)
    gender_requirement: str = "unknown"

    # Education (Jobinja only)
    education_level: str = "unknown"

    # Salary (original currency only — no FX conversion implemented)
    salary_min_original: float | None = None
    salary_max_original: float | None = None
    salary_currency_original: str = "IRR"

    # Skills (as Python lists, will be JSON in DB)
    skills_required: list[str] | None = None
    skills_preferred: list[str] | None = None
    technologies_mentioned: list[str] | None = None

    # Temporal
    posted_date: date | None = None
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

    # Identity
    id: int | None = None
    display_name_persian: str | None = None
    canonical_name: str | None = None

    # Lifecycle
    last_activity_date: date | None = None
    is_active: bool = True

    # Hiring metrics (refreshed by analytics_job)
    total_job_postings: int = 0
    active_job_postings: int = 0
    hiring_velocity_30d: float | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
