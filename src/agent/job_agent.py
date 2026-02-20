"""
Main job application agent.

Orchestrates: search → filter → apply → record.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode

from browser_use import Agent, Browser
from langchain_core.language_models.chat_models import BaseChatModel

from config import job_titles
from config.settings import (
    ACTION_DELAY,
    CHROME_PROFILE_PATH,
    HEADLESS,
    LLM_TIMEOUT,
    MAX_AGENT_STEPS,
    RESUME_PATH,
    RESUME_PDF_PATH,
)
from src.agent.actions import controller, set_llm
from src.models.schemas import RunSummary, TokenUsage
from src.utils.output import (
    accumulate_tokens,
    finalize_run_summary,
    init_run_summary,
    load_applied_urls,
)


def _browser_kwargs(*, keep_alive: bool = False) -> dict:
    """Return keyword arguments for constructing a Browser instance."""
    from pathlib import Path

    kwargs: dict = {"headless": HEADLESS}
    if keep_alive:
        kwargs["keep_alive"] = True
    if CHROME_PROFILE_PATH:
        profile_path = Path(CHROME_PROFILE_PATH)
        # Chrome expects user_data_dir to be the top-level data directory
        # (e.g. ~/.config/google-chrome) and profile_directory to be the
        # profile folder name inside it (e.g. "Profile 1").  If the user
        # supplied a path that ends with a profile folder, split them.
        if profile_path.name.startswith("Profile") or profile_path.name == "Default":
            kwargs["user_data_dir"] = str(profile_path.parent)
            kwargs["profile_directory"] = profile_path.name
        else:
            kwargs["user_data_dir"] = CHROME_PROFILE_PATH
    return kwargs


def _build_linkedin_search_url(search: dict) -> str:
    """Construct a LinkedIn Jobs search URL with all filters as query params."""
    params: dict[str, str] = {
        "keywords": search["title"],
        "location": search["location"],
    }
    date_map = {
        "past_24h": "r86400",
        "past_week": "r604800",
        "past_month": "r2592000",
    }
    if job_titles.DATE_POSTED in date_map:
        params["f_TPR"] = date_map[job_titles.DATE_POSTED]

    exp_map = {
        "entry": "2",
        "associate": "3",
        "mid_senior": "4",
        "director": "5",
        "executive": "6",
    }
    if job_titles.EXPERIENCE_LEVEL in exp_map:
        params["f_E"] = exp_map[job_titles.EXPERIENCE_LEVEL]

    if search.get("remote_only"):
        params["f_WT"] = "2"

    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)


# ── Initial actions builders (one per job board) ─────────────────────
# Each builder returns a list of browser-use action dicts for that board.
# Add new boards by adding a function and registering it in the map.

_INITIAL_ACTIONS_BUILDERS: dict[str, callable] = {}


def _linkedin_initial_actions(search: dict) -> list[dict]:
    url = _build_linkedin_search_url(search)
    return [{"navigate": {"url": url, "new_tab": False}}]


_INITIAL_ACTIONS_BUILDERS["linkedin"] = _linkedin_initial_actions


def _build_initial_actions(search: dict) -> list[dict] | None:
    """Return initial_actions for the current job board, or None if unsupported."""
    board = job_titles.JOB_BOARDS[0] if job_titles.JOB_BOARDS else "linkedin"
    builder = _INITIAL_ACTIONS_BUILDERS.get(board)
    if builder:
        return builder(search)
    return None


def _build_task_prompt(
    search: dict,
    *,
    use_initial_actions: bool = False,
    review_before_submit: bool = False,
) -> str:
    """Compose the natural-language task prompt for one search."""

    board = job_titles.JOB_BOARDS[0] if job_titles.JOB_BOARDS else "linkedin"
    board_url = {
        "linkedin": "https://www.linkedin.com/jobs",
        "indeed": "https://www.indeed.com",
    }.get(board, "https://www.linkedin.com/jobs")

    max_apply = job_titles.MAX_APPLICATIONS_PER_RUN
    max_review = job_titles.MAX_LISTINGS_TO_REVIEW
    skill_ratio = job_titles.MIN_SKILL_MATCH_RATIO

    if use_initial_actions:
        step2 = f"""\
## Step 2 — Search results
The browser has already navigated to the job board with the correct search
filters applied. You should now be on the search results page for
"{search['title']}" in "{search['location']}". Proceed directly to
reviewing the listings below."""
    else:
        date_filter = {
            "past_24h": "Filter by 'Past 24 hours'.",
            "past_week": "Filter by 'Past week'.",
            "past_month": "Filter by 'Past month'.",
            "any": "Do not filter by date.",
        }.get(job_titles.DATE_POSTED, "")
        exp_filter = (
            f"Filter by experience level: {job_titles.EXPERIENCE_LEVEL}."
            if job_titles.EXPERIENCE_LEVEL != "any"
            else ""
        )
        remote_filter = (
            "Filter for remote jobs only." if search.get("remote_only") else ""
        )
        step2 = f"""\
## Step 2 — Search for jobs
1. Navigate to {board_url}
2. Search for: "{search['title']}"
3. Location: "{search['location']}"
4. {date_filter}
5. {exp_filter}
6. {remote_filter}"""

    return f"""\
You are an autonomous job application assistant.

## Your Goal
Search for jobs and apply to every qualified position on behalf of the candidate.

## Step 1 — Read candidate data
1. Call the `read_resume` action to load the resume.
2. Call the `get_profile` action to load personal info and preferences.
   Keep this data in memory for filling forms.

{step2}

## Step 3 — Review listings (up to {max_review})
For each job listing:
1. Open the listing to read the full description.
2. Call `check_company` with the company name and job title — if "skip", call `save_skipped_job` with reason "company_blocked" and move on.
3. Call `check_job_description` with the full description — if "skip", call `save_skipped_job` with reason "keyword_blocked" and move on.
4. Evaluate whether the candidate is qualified: at least {int(skill_ratio * 100)}% of the candidate's skills should appear in the description.  If not qualified, call `save_skipped_job` with reason "not_qualified" and move on.

## Step 4 — Apply (up to {max_apply} successful applications)
For each qualified job:
1. Click the application button.
2. Fill all form fields using the profile data.  For screening questions, call `answer_screening_question` with the full question text.  The action returns both the candidate profile AND resume so you can answer questions that aren't directly in the profile.
3. **Track every screening question and your answer** as a key-value pair (question text → answer text).  You will pass these to `save_application` later.
4. When a file upload field appears for the resume, call `get_resume_file_path` to get the absolute path to the candidate's resume PDF, then upload that file. Do NOT generate or create your own resume — always use the file from `get_resume_file_path`.
5. If the application asks for a cover letter, call `make_cover_letter` with the job_title, company, location, and full job_description.  Use the returned text as the cover letter.  Add it to your screening answers dict with the exact form label as the key (e.g. "Cover Letter").
6. Review the filled form for accuracy.{"  Then call `ask_human` with a summary of the job (title, company, URL) and all your filled answers so the human can approve or reject before submitting.  If rejected, call `save_skipped_job` with reason 'human_rejected' and move on." if review_before_submit else ""}  Then submit.
7. After submitting, call `save_application` with all job details and pass `screening_answers` as a JSON string mapping each question to its answer (including the cover letter if one was generated).
8. If you encounter a CAPTCHA, login wall, or any blocker you cannot handle, call `ask_human` for help.  If the human skips, call `save_skipped_job` with the appropriate reason and move on.

## Important Rules
- NEVER fabricate information. Only use data from the resume and profile.
- NEVER generate your own resume file. Always use `get_resume_file_path` to get the candidate's actual resume for upload.
- Do NOT skip a job just because it lacks an "Easy Apply" button. Apply to all qualified jobs regardless of the application method.
- When a form field doesn't match any profile or resume data, leave it blank or call `ask_human`.
- If the site asks you to log in first, call `ask_human` with a message asking the user to log in.
- After each successful application, count how many you've completed.  Stop after {max_apply} successful applications.
- Be methodical: open each job in sequence, don't rush.
- Search query for logging: "{search['title']} in {search['location']}"
"""


def _build_apply_prompt(url: str, *, review_before_submit: bool = False) -> str:
    """Compose a task prompt to apply directly to a single job posting URL."""
    return f"""\
You are an autonomous job application assistant.

## Your Goal
Apply to a specific job posting on behalf of the candidate.

## Step 1 — Read candidate data
1. Call the `read_resume` action to load the resume.
2. Call the `get_profile` action to load personal info and preferences.
   Keep this data in memory for filling forms.

## Step 2 — Navigate to the job posting
1. Go directly to: {url}
2. Read the full job description.

## Step 3 — Evaluate the job
1. Call `check_company` with the company name and job title — if "skip", call `save_skipped_job` with reason "company_blocked" and stop.
2. Call `check_job_description` with the full description — if "skip", call `save_skipped_job` with reason "keyword_blocked" and stop.

## Step 4 — Apply
1. Click the application button.
2. Fill all form fields using the profile data. For screening questions, call `answer_screening_question` with the full question text.  The action returns both the candidate profile AND resume so you can answer questions that aren't directly in the profile.
3. **Track every screening question and your answer** as a key-value pair (question text → answer text).  You will pass these to `save_application` later.
4. When a file upload field appears for the resume, call `get_resume_file_path` to get the absolute path to the candidate's resume PDF, then upload that file. Do NOT generate or create your own resume — always use the file from `get_resume_file_path`.
5. If the application asks for a cover letter, call `make_cover_letter` with the job_title, company, location, and full job_description.  Use the returned text as the cover letter.  Add it to your screening answers dict with the exact form label as the key (e.g. "Cover Letter").
6. Review the filled form for accuracy.{"  Then call `ask_human` with a summary of the job (title, company, URL) and all your filled answers so the human can approve or reject before submitting.  If rejected, call `save_skipped_job` with reason 'human_rejected' and stop." if review_before_submit else ""}  Then submit.
7. After submitting, call `save_application` with all job details and pass `screening_answers` as a JSON string mapping each question to its answer (including the cover letter if one was generated).
8. If you encounter a CAPTCHA, login wall, or any blocker you cannot handle, call `ask_human` for help.

## Important Rules
- NEVER fabricate information. Only use data from the resume and profile.
- NEVER generate your own resume file. Always use `get_resume_file_path` to get the candidate's actual resume for upload.
- Do NOT skip a job just because it lacks an "Easy Apply" button. Apply to all qualified jobs regardless of the application method.
- When a form field doesn't match any profile or resume data, leave it blank or call `ask_human`.
- If the site asks you to log in first, call `ask_human` with a message asking the user to log in.
"""


async def run_single_apply(
    llm: BaseChatModel,
    url: str,
    *,
    keep_alive: bool = False,
    review_before_submit: bool = False,
) -> RunSummary:
    """Apply to a single job posting by URL.

    Parameters
    ----------
    llm:
        The LangChain chat model to use for the browser agent.
    url:
        Direct URL to the job posting.

    Returns
    -------
    RunSummary with stats for the single application.
    """
    set_llm(llm)
    summary = init_run_summary()

    print(f"\n{'='*60}")
    print(f"  Applying to: {url}")
    print(f"{'='*60}\n")

    task = _build_apply_prompt(url, review_before_submit=review_before_submit)

    # Each Agent gets its own Browser so its lifecycle (start/kill) is
    # self-contained — browser_use 0.11.x kills the browser session when
    # Agent.run() finishes.
    agent = Agent(
        task=task,
        llm=llm,
        browser=Browser(**_browser_kwargs(keep_alive=keep_alive)),
        controller=controller,
        available_file_paths=[str(RESUME_PDF_PATH.resolve())],
        step_timeout=86400,
        llm_timeout=LLM_TIMEOUT,
    )

    history = await agent.run(max_steps=MAX_AGENT_STEPS)

    # Accumulate token usage and flush to disk
    accumulate_tokens(history.usage)

    result = history.final_result()
    if result:
        print(f"\nAgent summary: {result[:500]}")

    t = summary.token_usage
    print(f"\n{'─'*40}")
    print(f"  Token Usage")
    print(f"{'─'*40}")
    print(f"  Input:   {t.input_tokens:,}")
    print(f"  Output:  {t.output_tokens:,}")
    print(f"  Cached:  {t.cached_tokens:,}")
    print(f"  Total:   {t.total_tokens:,}")
    print(f"  Cost:    ${t.total_cost:.4f}")
    print(f"{'─'*40}")

    summary_path = finalize_run_summary()
    print(f"\nRun summary saved to {summary_path}")

    return summary


async def run_job_search(
    llm: BaseChatModel,
    searches: list[dict] | None = None,
    *,
    keep_alive: bool = False,
    use_initial_actions: bool = False,
    review_before_submit: bool = False,
) -> RunSummary:
    """Run the full job-search-and-apply pipeline.

    Parameters
    ----------
    llm:
        The LangChain chat model to use for the browser agent.
    searches:
        Override the search list from config.  Defaults to
        ``job_titles.SEARCHES``.
    use_initial_actions:
        When *True*, navigate to the search results page via browser-use
        ``initial_actions`` instead of letting the LLM handle it.  Saves
        tokens but requires a supported job board (currently LinkedIn).

    Returns
    -------
    RunSummary with aggregate stats.
    """
    set_llm(llm)
    searches = searches or job_titles.SEARCHES
    summary = init_run_summary()
    browser_kw = _browser_kwargs(keep_alive=keep_alive)

    for search in searches:
        print(f"\n{'='*60}")
        print(f"  Searching: {search['title']} — {search['location']}")
        print(f"{'='*60}\n")

        initial_actions = (
            _build_initial_actions(search) if use_initial_actions else None
        )
        task = _build_task_prompt(
            search,
            use_initial_actions=initial_actions is not None,
            review_before_submit=review_before_submit,
        )

        # Each Agent gets its own Browser so its lifecycle (start/kill)
        # is self-contained — browser_use 0.11.x kills the browser
        # session when Agent.run() finishes.
        agent_kwargs: dict = dict(
            task=task,
            llm=llm,
            browser=Browser(**browser_kw),
            controller=controller,
            available_file_paths=[str(RESUME_PDF_PATH.resolve())],
            step_timeout=86400,
            llm_timeout=LLM_TIMEOUT,
        )
        if initial_actions:
            agent_kwargs["initial_actions"] = initial_actions

        agent = Agent(**agent_kwargs)

        history = await agent.run(max_steps=MAX_AGENT_STEPS)

        # Accumulate token usage and flush to disk
        accumulate_tokens(history.usage)

        print(f"\n--- Search complete: {search['title']} ---")
        result = history.final_result()
        if result:
            print(f"Agent summary: {result[:500]}")

    # Print token usage summary
    t = summary.token_usage
    print(f"\n{'─'*40}")
    print(f"  Token Usage")
    print(f"{'─'*40}")
    print(f"  Input:   {t.input_tokens:,}")
    print(f"  Output:  {t.output_tokens:,}")
    print(f"  Cached:  {t.cached_tokens:,}")
    print(f"  Total:   {t.total_tokens:,}")
    print(f"  Cost:    ${t.total_cost:.4f}")
    print(f"{'─'*40}")

    # Finalize and save the run summary
    summary_path = finalize_run_summary()
    print(f"\nRun summary saved to {summary_path}")

    return summary
