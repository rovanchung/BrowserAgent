"""
Candidate profile — single source of truth for all personal data,
preferences, and screening-question answers used by the agent.
"""

PROFILE: dict = {
    # ── Personal Information ─────────────────────────────────────────
    "first_name": "Jane",
    "last_name": "Doe",
    "preferred_first_name": "Jane",
    "pronouns": "she/her/hers",
    "email": "jane.doe@example.com",
    "phone": "+1-555-123-4567",
    "location": "San Francisco, CA",
    "linkedin_url": "https://www.linkedin.com/in/janedoe/",
    "github_url": "https://github.com/janedoe",
    "portfolio_url": "",
    # ── Work Authorization ───────────────────────────────────────────
    "work_authorization": "US Citizen",  # e.g. "US Citizen", "Green Card", "H1B"
    "requires_sponsorship": False,
    # ── Demographics (optional) ──────────────────────────────────────
    "gender": "Female",
    "race_ethnicity": "Prefer not to say",
    "veteran_status": "Not a veteran",
    "disability_status": "No",
    # ── Education ────────────────────────────────────────────────────
    "education": [
        {
            "degree": "Bachelor's Degree in Computer Science",
            "school": "University of California, Berkeley",
            "graduation_year": 2019,
        },
    ],
    # ── Experience ───────────────────────────────────────────────────
    "years_of_experience": 5,
    "current_title": "Software Engineer",
    "current_company": "Acme Corp",
    "notice_period": "2 weeks",
    "skills": ["Python", "JavaScript", "React", "PostgreSQL", "AWS"],
    # ── Salary ───────────────────────────────────────────────────────
    "desired_salary_min": 150_000,  # USD per year
    "salary_currency": "USD",
    "open_to_negotiation": True,
    # ── Preferences ──────────────────────────────────────────────────
    "willing_to_relocate": False,
    "open_to_remote": True,
    "open_to_hybrid": True,
    "open_to_onsite": False,
    "earliest_start_date": "2 weeks",
    # ── Screening Defaults ───────────────────────────────────────────
    "how_did_you_hear": "LinkedIn",
    "has_referral": False,
    # ── Filters ──────────────────────────────────────────────────────
    "companies_to_skip": ["ExampleCorp"],
    "keywords_to_avoid": [],
}
