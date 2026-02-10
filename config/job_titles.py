"""
Target job titles and search parameters.

The agent iterates through SEARCHES, running each one on the
configured job boards. Each search produces a list of job listings
that are then filtered and applied to.
"""

# ── Job Searches ─────────────────────────────────────────────────────
# Each entry defines one search the agent will perform.
SEARCHES = [
    {
        "title": "Senior Software Engineer",
        "location": "San Francisco, CA",
        "remote_only": True,
    },
    {
        "title": "Staff Software Engineer",
        "location": "Remote",
        "remote_only": True,
    },
    {
        "title": "Backend Engineer",
        "location": "San Francisco, CA",
        "remote_only": False,
    },
]

# ── Job Boards ───────────────────────────────────────────────────────
# Which platforms to search. The agent uses the appropriate strategy
# for each board.
#
# Supported values: "linkedin", "indeed"
# (more boards can be added by implementing new strategies in src/agent/)
JOB_BOARDS = [
    "linkedin",
]

# ── Search Filters ───────────────────────────────────────────────────
DATE_POSTED = "past_week"  # "past_24h", "past_week", "past_month", "any"
EXPERIENCE_LEVEL = (
    "mid_senior"  # "entry", "associate", "mid_senior", "director", "executive", "any"
)
MAX_APPLICATIONS_PER_RUN = 10  # Stop after this many successful applications per run
MAX_LISTINGS_TO_REVIEW = 30  # Max listings to review per search before moving on

# ── Qualification Matching ───────────────────────────────────────────
# Minimum fraction of your skills that must appear in the job description
# for the agent to consider you "qualified". Range 0.0 - 1.0.
# Lower = more applications, higher = more selective.
MIN_SKILL_MATCH_RATIO = 0.3

# ── Required Keywords ────────────────────────────────────────────────
# At least ONE of these must appear in the job description (case-insensitive).
# Leave empty to skip this filter.
REQUIRED_KEYWORDS = [
    # "python",
    # "backend",
]
