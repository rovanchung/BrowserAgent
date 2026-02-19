"""
Custom browser-use actions available to the agent.

These actions extend what the agent can do beyond basic browser
interaction — saving data, reading local files, asking the human, etc.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from browser_use import ActionResult, Agent, Controller
from pydantic import BaseModel, ConfigDict

from config.profile import PROFILE
from config.settings import PROJECT_ROOT, RESUME_PATH, RESUME_PDF_PATH, SKIP_MATCH_TOLERANCE

PROFILE_PATH = PROJECT_ROOT / "config" / "profile.py"


def _levenshtein(a: str, b: str) -> int:
    """Return the Levenshtein edit-distance between two strings."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def _fuzzy_contains(haystack: str, needle: str, tolerance: int) -> bool:
    """Check if *needle* appears in *haystack* within *tolerance* edits.

    For exact mode (tolerance=0) this is a simple substring check.
    For fuzzy mode it slides a window over *haystack* and checks the
    Levenshtein distance of each window against *needle*.
    """
    if tolerance == 0:
        return needle in haystack
    if not needle:
        return True
    n = len(needle)
    for start in range(len(haystack) - n + 1 + tolerance):
        for end in range(start + max(1, n - tolerance), start + n + tolerance + 1):
            window = haystack[start:end]
            if _levenshtein(window, needle) <= tolerance:
                return True
    return False
from src.models.schemas import (
    ApplicationRecord,
    ApplicationStatus,
    JobListing,
    SkipReason,
)
from src.utils.cover_letter import generate_cover_letter
from src.utils.output import (
    flush_run_summary,
    get_run_summary,
    save_cover_letter_file,
    save_record,
)

# Module-level LLM reference, set by job_agent before running.
_llm = None


def set_llm(llm) -> None:
    """Store the LLM so actions can use it for cover-letter generation."""
    global _llm
    _llm = llm


controller = Controller()


class _NoParams(BaseModel):
    """Param model for actions that take no real arguments.

    Uses ``extra='allow'`` so the LLM can pass arbitrary fields (e.g.
    ``_placeholder``) without Pydantic rejecting them.  browser-use's
    default ``ActionModel`` uses ``extra='forbid'`` which causes
    validation errors for zero-parameter actions.
    """

    model_config = ConfigDict(extra="allow")


def _add_company_skip_entry(job_title: str, company: str) -> None:
    """Append a 'title:company' entry to companies_to_skip in config/profile.py.

    Modifies the file on disk and updates the in-memory PROFILE dict so the
    agent won't re-apply to the same job within the same run.
    """
    entry = f"{job_title}:{company}"

    # Update in-memory list
    skip_list = PROFILE.setdefault("companies_to_skip", [])
    if entry in skip_list:
        return
    skip_list.append(entry)

    # Persist to config/profile.py
    try:
        text = PROFILE_PATH.read_text(encoding="utf-8")
        # Find the closing bracket of companies_to_skip list and insert before it
        pattern = r"(\"companies_to_skip\"\s*:\s*\[)(.*?)(\s*\])"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            escaped = entry.replace('"', '\\"')
            new_text = (
                text[: match.end(2)] + f'\n        "{escaped}",' + text[match.end(2) :]
            )
            PROFILE_PATH.write_text(new_text, encoding="utf-8")
    except Exception:
        pass  # Non-critical — in-memory update is enough for this run


@controller.action("Read the candidate's resume from disk", param_model=_NoParams)
def read_resume() -> ActionResult:
    """Return the full text of the resume file."""
    path = RESUME_PATH
    if not path.exists():
        return ActionResult(
            extracted_content=f"ERROR: Resume not found at {path}. "
            "Please place resume.pdf in the resume/ folder and re-run.",
            error=f"Resume file not found: {path}",
        )
    text = path.read_text(encoding="utf-8")
    return ActionResult(extracted_content=text)


@controller.action(
    "Get the absolute file path of the candidate's resume PDF for uploading to file input fields. "
    "Call this whenever you need to upload a resume file.",
    param_model=_NoParams,
)
def get_resume_file_path() -> ActionResult:
    """Return the absolute path to the candidate's resume PDF."""
    path = RESUME_PDF_PATH
    if not path.exists():
        return ActionResult(
            extracted_content=f"ERROR: Resume PDF not found at {path}. "
            "Please place your resume.pdf in the resume/ folder.",
            error=f"Resume PDF not found: {path}",
        )
    return ActionResult(extracted_content=str(path.resolve()))


@controller.action("Get the candidate's personal profile for filling application forms", param_model=_NoParams)
def get_profile() -> ActionResult:
    """Return the full candidate profile as JSON."""
    return ActionResult(extracted_content=json.dumps(PROFILE, indent=2))


@controller.action(
    "Look up the answer to a screening question using the candidate profile and resume. "
    "Pass the full question text and get back the profile and resume data to answer it."
)
def answer_screening_question(question: str) -> ActionResult:
    """Return the profile and resume so the agent can answer any screening question."""
    resume_text = ""
    if RESUME_PATH.exists():
        resume_text = RESUME_PATH.read_text(encoding="utf-8")

    return ActionResult(
        extracted_content=(
            f"Answer the following screening question using the candidate profile and resume below.\n"
            f"Question: {question}\n\n"
            f"IMPORTANT: Always answer in the way most favorable to the candidate's application. "
            f"If the question asks about potential conflicts, obstacles, or negative factors "
            f"(e.g. competing obligations, criminal history, non-competes), "
            f"answer in the positive/clean direction (e.g. 'No' to conflicts, 'Yes' to willingness) "
            f"unless the profile or resume explicitly states otherwise.\n\n"
            f"Profile:\n{json.dumps(PROFILE, indent=2)}\n\n"
            f"Resume:\n{resume_text}"
        )
    )


@controller.action(
    "Save a successful job application. Call this after submitting an application. "
    "Provide job_title, company, location, url, job_board, search_query, and "
    "screening_answers (a JSON string mapping each question to its answer, "
    "including the cover letter if one was generated)."
)
def save_application(
    job_title: str,
    company: str,
    location: str = "",
    url: str = "",
    job_board: str = "",
    search_query: str = "",
    screening_answers: str = "{}",
) -> ActionResult:
    """Persist a successful application to the output log."""
    try:
        answers = json.loads(screening_answers)
    except (json.JSONDecodeError, TypeError):
        answers = {}

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
        screening_answers=answers,
    )
    log_path = save_record(record)
    cl_path = save_cover_letter_file(record)

    # Add to companies_to_skip so we don't re-apply to the same job
    _add_company_skip_entry(job_title, company)

    # Update the active run summary in real-time
    summary = get_run_summary()
    if summary is not None:
        summary.applications.append(record)
        summary.total_applied += 1
        summary.total_reviewed += 1
        flush_run_summary()

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

    # Update the active run summary in real-time
    summary = get_run_summary()
    if summary is not None:
        summary.applications.append(record)
        summary.total_skipped += 1
        summary.total_reviewed += 1
        flush_run_summary()

    return ActionResult(
        extracted_content=f"Skipped: {job_title} at {company} ({skip_reason.value})"
    )


@controller.action(
    "Check whether a company+job should be skipped (blocked list). "
    "Pass the company_name and job_title. Returns 'skip' or 'ok'."
)
def check_company(company_name: str, job_title: str = "") -> ActionResult:
    """Check the company (and optionally job title) against the user's block list.

    Each entry in companies_to_skip uses the format ``"title_pattern:company_pattern"``.
    A title_pattern of ``*`` matches any job title at that company.
    """
    tol = SKIP_MATCH_TOLERANCE
    company_lower = company_name.lower()
    title_lower = job_title.lower()
    for entry in PROFILE.get("companies_to_skip", []):
        if ":" in entry:
            title_pat, company_pat = entry.split(":", 1)
        else:
            # Bare string → treat as wildcard company match (backward compat)
            title_pat, company_pat = "*", entry
        if _fuzzy_contains(company_lower, company_pat.strip().lower(), tol):
            if title_pat.strip() == "*" or _fuzzy_contains(title_lower, title_pat.strip().lower(), tol):
                return ActionResult(extracted_content="skip")
    return ActionResult(extracted_content="ok")


@controller.action(
    "Check whether a job description contains blocked keywords. "
    "Pass the full description text. Returns 'skip' or 'ok'."
)
def check_job_description(description: str) -> ActionResult:
    """Screen a job description against blocked keywords."""
    desc_lower = description.lower()
    for kw in PROFILE.get("keywords_to_avoid", []):
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


@controller.action(
    "Generate a tailored cover letter for a job. Provide the job_title, company, "
    "location, and the full job_description. Returns the cover letter text."
)
async def make_cover_letter(
    job_title: str,
    company: str,
    location: str,
    job_description: str,
) -> ActionResult:
    """Use the dedicated cover-letter generator to produce a tailored letter."""
    if _llm is None:
        return ActionResult(
            extracted_content="ERROR: LLM not available for cover letter generation.",
            error="LLM not configured in actions module.",
        )

    resume_text = ""
    if RESUME_PATH.exists():
        resume_text = RESUME_PATH.read_text(encoding="utf-8")

    job = JobListing(
        title=job_title,
        company=company,
        location=location,
        description=job_description,
    )
    letter = await generate_cover_letter(_llm, job, resume_text)
    return ActionResult(extracted_content=letter)
