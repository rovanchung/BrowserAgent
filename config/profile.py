"""
Your personal profile for job applications.

Fill in every field that applies to you. The agent uses this data to:
  - Auto-fill application forms
  - Answer screening questions
  - Generate tailored cover letters
"""

# ── Personal Information ─────────────────────────────────────────────
FIRST_NAME = "Jane"
LAST_NAME = "Doe"
EMAIL = "jane.doe@email.com"
PHONE = "+1-555-012-3456"
LOCATION = "San Francisco, CA"
LINKEDIN_URL = "https://linkedin.com/in/janedoe"
GITHUB_URL = "https://github.com/janedoe"
PORTFOLIO_URL = ""  # leave blank if N/A

# ── Work Authorization ───────────────────────────────────────────────
WORK_AUTHORIZATION = "US Citizen"  # e.g. "US Citizen", "Green Card", "H1B", "OPT/CPT", "Require Sponsorship"
REQUIRES_SPONSORSHIP = False

# ── Demographics (optional — leave blank to skip) ────────────────────
GENDER = ""            # e.g. "Male", "Female", "Non-binary", "Prefer not to say"
RACE_ETHNICITY = ""    # e.g. "Asian", "White", "Prefer not to say"
VETERAN_STATUS = ""    # e.g. "Not a veteran", "Veteran", "Prefer not to say"
DISABILITY_STATUS = "" # e.g. "No", "Yes", "Prefer not to say"

# ── Education ────────────────────────────────────────────────────────
EDUCATION = [
    {
        "degree": "M.S. Computer Science",
        "school": "Stanford University",
        "graduation_year": 2020,
    },
    {
        "degree": "B.S. Computer Science",
        "school": "UC Berkeley",
        "graduation_year": 2018,
    },
]

# ── Experience Summary ───────────────────────────────────────────────
YEARS_OF_EXPERIENCE = 6
CURRENT_TITLE = "Senior Software Engineer"
CURRENT_COMPANY = "Acme Corp"
NOTICE_PERIOD = "2 weeks"

# ── Skills ───────────────────────────────────────────────────────────
SKILLS = [
    "Python", "TypeScript", "Go",
    "React", "Next.js", "Node.js",
    "AWS", "GCP", "Kubernetes", "Docker",
    "PostgreSQL", "Redis", "Kafka",
    "System Design", "CI/CD", "Terraform",
]

# ── Salary Expectations ──────────────────────────────────────────────
DESIRED_SALARY_MIN = 150_000  # USD per year
DESIRED_SALARY_MAX = 200_000
SALARY_CURRENCY = "USD"
OPEN_TO_NEGOTIATION = True

# ── Preferences ──────────────────────────────────────────────────────
WILLING_TO_RELOCATE = False
OPEN_TO_REMOTE = True
OPEN_TO_HYBRID = True
OPEN_TO_ONSITE = False
EARLIEST_START_DATE = "2 weeks from offer"

# ── Screening Question Auto-Answers ──────────────────────────────────
# Maps keyword patterns (case-insensitive) found in screening questions
# to the answer the agent should provide.
#
# The agent matches questions by checking if ANY keyword in the key
# appears in the question text, then uses the corresponding answer.
# Put more specific patterns first — first match wins.
#
# Examples:
#   "how many years" in question → answer "6"
#   "authorized to work" in question → answer "Yes"
QUESTION_ANSWERS = {
    # Work authorization
    "authorized to work": "Yes",
    "sponsorship": "No",
    "legally authorized": "Yes",
    "right to work": "Yes",
    "work permit": "Yes, I am authorized to work",

    # Experience
    "years of experience": str(YEARS_OF_EXPERIENCE),
    "how many years": str(YEARS_OF_EXPERIENCE),

    # Availability
    "start date": EARLIEST_START_DATE,
    "when can you start": EARLIEST_START_DATE,
    "notice period": NOTICE_PERIOD,
    "available to start": EARLIEST_START_DATE,

    # Location / Remote
    "willing to relocate": "No" if not WILLING_TO_RELOCATE else "Yes",
    "work remotely": "Yes" if OPEN_TO_REMOTE else "No",
    "remote work": "Yes" if OPEN_TO_REMOTE else "No",
    "commute": "Yes" if OPEN_TO_ONSITE or OPEN_TO_HYBRID else "No, I prefer remote",
    "on-site": "Yes" if OPEN_TO_ONSITE else "No",
    "hybrid": "Yes" if OPEN_TO_HYBRID else "No",

    # Salary
    "salary expectation": f"{DESIRED_SALARY_MIN:,}-{DESIRED_SALARY_MAX:,} {SALARY_CURRENCY}",
    "desired salary": f"{DESIRED_SALARY_MIN:,}-{DESIRED_SALARY_MAX:,} {SALARY_CURRENCY}",
    "compensation expectation": f"{DESIRED_SALARY_MIN:,}-{DESIRED_SALARY_MAX:,} {SALARY_CURRENCY}",

    # Education
    "highest degree": EDUCATION[0]["degree"] if EDUCATION else "",
    "degree": EDUCATION[0]["degree"] if EDUCATION else "",

    # General
    "cover letter": "",  # left blank — agent generates per-job cover letters
    "additional information": "",
    "anything else": "",
    "how did you hear": "Online job search",
    "referral": "No",
    "referred by": "N/A",
}

# ── Companies to Skip ────────────────────────────────────────────────
# The agent will not apply to these companies (case-insensitive match).
COMPANIES_TO_SKIP = [
    # "Current Employer Inc.",
]

# ── Keywords to Avoid in Job Descriptions ────────────────────────────
# If any of these appear in the job description, the agent skips the job.
KEYWORDS_TO_AVOID = [
    "security clearance required",
    "top secret",
    "ts/sci",
]
