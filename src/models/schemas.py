"""
Data models used throughout the application.

All structured data flows through these Pydantic models so that
output files are always consistent and machine-readable.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────

class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


class SkipReason(str, Enum):
    NOT_QUALIFIED = "not_qualified"
    COMPANY_BLOCKED = "company_blocked"
    KEYWORD_BLOCKED = "keyword_blocked"
    CAPTCHA = "captcha"
    LOGIN_REQUIRED = "login_required"
    ALREADY_APPLIED = "already_applied"
    AGENT_ERROR = "agent_error"
    UNKNOWN = "unknown"


# ── Job Listing ──────────────────────────────────────────────────────

class JobListing(BaseModel):
    """A single job listing discovered during search."""

    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    salary_range: str = ""
    posted_date: str = ""
    job_board: str = ""
    search_query: str = ""


# ── Application Record ───────────────────────────────────────────────

class ApplicationRecord(BaseModel):
    """One application attempt — saved to the output log."""

    job: JobListing
    status: ApplicationStatus
    skip_reason: SkipReason | None = None
    cover_letter: str = ""
    applied_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""


# ── Run Summary ──────────────────────────────────────────────────────

class RunSummary(BaseModel):
    """Aggregated stats for a single agent run."""

    run_started: str = Field(default_factory=lambda: datetime.now().isoformat())
    run_finished: str = ""
    total_reviewed: int = 0
    total_applied: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    applications: list[ApplicationRecord] = Field(default_factory=list)
