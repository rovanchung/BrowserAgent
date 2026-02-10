"""
Custom browser-use actions available to the agent.

These actions extend what the agent can do beyond basic browser
interaction — saving data, reading local files, asking the human, etc.
"""

from __future__ import annotations

import json
from pathlib import Path

from browser_use import ActionResult, Agent, Controller

from config import profile
from config.settings import RESUME_PATH
from src.models.schemas import (
    ApplicationRecord,
    ApplicationStatus,
    JobListing,
    SkipReason,
)
from src.utils.output import save_cover_letter, save_record

controller = Controller()


@controller.action("Read the candidate's resume from disk")
def read_resume() -> ActionResult:
    """Return the full text of the resume file."""
    path = RESUME_PATH
    if not path.exists():
        return ActionResult(
            extracted_content=f"ERROR: Resume not found at {path}. "
            "Please create resume/resume.md first.",
            error=f"Resume file not found: {path}",
        )
    text = path.read_text(encoding="utf-8")
    return ActionResult(extracted_content=text)


@controller.action("Get the candidate's personal profile for filling application forms")
def get_profile() -> ActionResult:
    """Return structured profile data the agent needs for form-filling."""
    data = {
        "first_name": profile.FIRST_NAME,
        "last_name": profile.LAST_NAME,
        "full_name": f"{profile.FIRST_NAME} {profile.LAST_NAME}",
        "email": profile.EMAIL,
        "phone": profile.PHONE,
        "location": profile.LOCATION,
        "linkedin": profile.LINKEDIN_URL,
        "github": profile.GITHUB_URL,
        "portfolio": profile.PORTFOLIO_URL,
        "work_authorization": profile.WORK_AUTHORIZATION,
        "requires_sponsorship": profile.REQUIRES_SPONSORSHIP,
        "years_of_experience": profile.YEARS_OF_EXPERIENCE,
        "current_title": profile.CURRENT_TITLE,
        "current_company": profile.CURRENT_COMPANY,
        "skills": profile.SKILLS,
        "education": profile.EDUCATION,
        "desired_salary": f"{profile.DESIRED_SALARY_MIN:,}+ {profile.SALARY_CURRENCY}",
        "earliest_start_date": profile.EARLIEST_START_DATE,
        "willing_to_relocate": profile.WILLING_TO_RELOCATE,
        "open_to_remote": profile.OPEN_TO_REMOTE,
    }
    return ActionResult(extracted_content=json.dumps(data, indent=2))


@controller.action(
    "Look up the answer to a screening question using keyword matching. "
    "Pass the full question text and get back the best-match answer."
)
def answer_screening_question(question: str) -> ActionResult:
    """Match a screening question against the configured keyword→answer map."""
    question_lower = question.lower()
    for keyword, answer in profile.QUESTION_ANSWERS.items():
        if keyword.lower() in question_lower:
            return ActionResult(extracted_content=f"Answer: {answer}")
    return ActionResult(
        extracted_content="No pre-configured answer found for this question. "
        "Use your best judgment based on the candidate's profile and resume."
    )


@controller.action(
    "Save a successful job application. Call this after submitting an application. "
    "Provide job_title, company, location, url, job_board, search_query, and cover_letter."
)
def save_application(
    job_title: str,
    company: str,
    location: str = "",
    url: str = "",
    job_board: str = "",
    search_query: str = "",
    cover_letter: str = "",
) -> ActionResult:
    """Persist a successful application to the output log."""
    record = ApplicationRecord(
        job=JobListing(
            title=job_title,
            company=company,
            location=location,
            url=url,
            job_board=job_board,
            search_query=search_query,
        ),
        status=ApplicationStatus.APPLIED,
        cover_letter=cover_letter,
    )
    log_path = save_record(record)
    cl_path = save_cover_letter(record)
    msg = f"Application saved to {log_path}"
    if cl_path:
        msg += f" | Cover letter saved to {cl_path}"
    return ActionResult(extracted_content=msg)


@controller.action(
    "Record a skipped job (not qualified, blocked company, captcha, etc.). "
    "Provide job_title, company, url, and reason."
)
def save_skipped_job(
    job_title: str,
    company: str,
    url: str = "",
    reason: str = "unknown",
    notes: str = "",
) -> ActionResult:
    """Persist a skipped-job record to the output log."""
    reason_map = {v.value: v for v in SkipReason}
    skip_reason = reason_map.get(reason, SkipReason.UNKNOWN)

    record = ApplicationRecord(
        job=JobListing(title=job_title, company=company, url=url),
        status=ApplicationStatus.SKIPPED,
        skip_reason=skip_reason,
        notes=notes,
    )
    save_record(record)
    return ActionResult(
        extracted_content=f"Skipped: {job_title} at {company} ({skip_reason.value})"
    )


@controller.action(
    "Check whether a company should be skipped (blocked list). "
    "Returns 'skip' or 'ok'."
)
def check_company(company_name: str) -> ActionResult:
    """Check the company against the user's block list."""
    for blocked in profile.COMPANIES_TO_SKIP:
        if blocked.lower() in company_name.lower():
            return ActionResult(extracted_content="skip")
    return ActionResult(extracted_content="ok")


@controller.action(
    "Check whether a job description contains blocked keywords. "
    "Pass the full description text. Returns 'skip' or 'ok'."
)
def check_job_description(description: str) -> ActionResult:
    """Screen a job description against blocked keywords."""
    desc_lower = description.lower()
    for kw in profile.KEYWORDS_TO_AVOID:
        if kw.lower() in desc_lower:
            return ActionResult(
                extracted_content=f"skip — matched blocked keyword: {kw}"
            )
    return ActionResult(extracted_content="ok")


@controller.action(
    "Ask the human user for help (e.g. CAPTCHA, login, ambiguous question)"
)
def ask_human(message: str) -> ActionResult:
    """Pause and ask the user for input."""
    print(f"\n{'='*60}")
    print(f"AGENT NEEDS HELP: {message}")
    print(f"{'='*60}")
    user_input = input("Your response (or press Enter to skip): ").strip()
    if not user_input:
        return ActionResult(extracted_content="User skipped. Move on to the next task.")
    return ActionResult(extracted_content=f"User responded: {user_input}")
