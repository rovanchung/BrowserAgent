"""
Main job application agent.

Orchestrates: search → filter → apply → record.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from browser_use import Agent, Browser
from langchain_core.language_models.chat_models import BaseChatModel

from config import job_titles, profile
from config.settings import (
    ACTION_DELAY,
    CHROME_PROFILE_PATH,
    GENERATE_COVER_LETTER,
    HEADLESS,
    MAX_AGENT_STEPS,
    RESUME_PATH,
)
from src.agent.actions import controller
from src.models.schemas import RunSummary, TokenUsage
from src.utils.cover_letter import generate_cover_letter
from src.utils.output import load_applied_urls, save_run_summary


def _build_browser() -> Browser:
    """Create a Browser instance with the user's configuration."""
    from pathlib import Path

    kwargs: dict = {"headless": HEADLESS}
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
    return Browser(**kwargs)


def _build_task_prompt(search: dict) -> str:
    """Compose the natural-language task prompt for one search."""

    board = job_titles.JOB_BOARDS[0] if job_titles.JOB_BOARDS else "linkedin"
    board_url = {
        "linkedin": "https://www.linkedin.com/jobs",
        "indeed": "https://www.indeed.com",
    }.get(board, "https://www.linkedin.com/jobs")

    date_filter_instruction = {
        "past_24h": "Filter by 'Past 24 hours'.",
        "past_week": "Filter by 'Past week'.",
        "past_month": "Filter by 'Past month'.",
        "any": "Do not filter by date.",
    }.get(job_titles.DATE_POSTED, "")

    exp_instruction = ""
    if job_titles.EXPERIENCE_LEVEL != "any":
        exp_instruction = f"Filter by experience level: {job_titles.EXPERIENCE_LEVEL}."

    remote_instruction = ""
    if search.get("remote_only"):
        remote_instruction = "Filter for remote jobs only."

    max_apply = job_titles.MAX_APPLICATIONS_PER_RUN
    max_review = job_titles.MAX_LISTINGS_TO_REVIEW
    skill_ratio = job_titles.MIN_SKILL_MATCH_RATIO

    return f"""\
You are an autonomous job application assistant.

## Your Goal
Search for jobs and apply to every qualified position on behalf of the candidate.

## Step 1 — Read candidate data
1. Call the `read_resume` action to load the resume.
2. Call the `get_profile` action to load personal info and preferences.
   Keep this data in memory for filling forms.

## Step 2 — Search for jobs
1. Navigate to {board_url}
2. Search for: "{search['title']}"
3. Location: "{search['location']}"
4. {date_filter_instruction}
5. {exp_instruction}
6. {remote_instruction}

## Step 3 — Review listings (up to {max_review})
For each job listing:
1. Open the listing to read the full description.
2. Call `check_company` with the company name — if "skip", call `save_skipped_job` with reason "company_blocked" and move on.
3. Call `check_job_description` with the full description — if "skip", call `save_skipped_job` with reason "keyword_blocked" and move on.
4. Evaluate whether the candidate is qualified: at least {int(skill_ratio * 100)}% of the candidate's skills should appear in the description.  If not qualified, call `save_skipped_job` with reason "not_qualified" and move on.

## Step 4 — Apply (up to {max_apply} successful applications)
For each qualified job:
1. Click "Easy Apply" or the application button.
2. Fill all form fields using the profile data.  For screening questions, call `answer_screening_question` with the full question text.
3. Upload the resume when a file upload field appears.
4. If the application asks for a cover letter, write a brief, tailored cover letter using the job description and the candidate's resume.
5. Review the filled form for accuracy, then submit.
6. After submitting, call `save_application` with all job details and the cover letter text.
7. If you encounter a CAPTCHA, login wall, or any blocker you cannot handle, call `ask_human` for help.  If the human skips, call `save_skipped_job` with the appropriate reason and move on.

## Important Rules
- NEVER fabricate information. Only use data from the resume and profile.
- When a form field doesn't match any profile data, leave it blank or call `ask_human`.
- If the site asks you to log in first, call `ask_human` with a message asking the user to log in.
- After each successful application, count how many you've completed.  Stop after {max_apply} successful applications.
- Be methodical: open each job in sequence, don't rush.
- Search query for logging: "{search['title']} in {search['location']}"
"""


def _build_apply_prompt(url: str) -> str:
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
1. Call `check_company` with the company name — if "skip", call `save_skipped_job` with reason "company_blocked" and stop.
2. Call `check_job_description` with the full description — if "skip", call `save_skipped_job` with reason "keyword_blocked" and stop.

## Step 4 — Apply
1. Click "Easy Apply" or the application button.
2. Fill all form fields using the profile data. For screening questions, call `answer_screening_question` with the full question text.
3. Upload the resume when a file upload field appears.
4. If the application asks for a cover letter, write a brief, tailored cover letter using the job description and the candidate's resume.
5. Review the filled form for accuracy, then submit.
6. After submitting, call `save_application` with all job details and the cover letter text.
7. If you encounter a CAPTCHA, login wall, or any blocker you cannot handle, call `ask_human` for help.

## Important Rules
- NEVER fabricate information. Only use data from the resume and profile.
- When a form field doesn't match any profile data, leave it blank or call `ask_human`.
- If the site asks you to log in first, call `ask_human` with a message asking the user to log in.
"""


async def run_single_apply(
    llm: BaseChatModel,
    url: str,
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
    summary = RunSummary()
    browser = _build_browser()

    try:
        print(f"\n{'='*60}")
        print(f"  Applying to: {url}")
        print(f"{'='*60}\n")

        task = _build_apply_prompt(url)

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            controller=controller,
        )

        history = await agent.run(max_steps=MAX_AGENT_STEPS)

        if history.usage:
            u = history.usage
            summary.token_usage.input_tokens += u.total_prompt_tokens
            summary.token_usage.output_tokens += u.total_completion_tokens
            summary.token_usage.cached_tokens += u.total_prompt_cached_tokens
            summary.token_usage.total_tokens += u.total_tokens
            summary.token_usage.total_cost += u.total_cost

        result = history.final_result()
        if result:
            print(f"\nAgent summary: {result[:500]}")
    finally:
        await browser.stop()

    summary.run_finished = datetime.now().isoformat()

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

    summary_path = save_run_summary(summary)
    print(f"\nRun summary saved to {summary_path}")

    return summary


async def run_job_search(
    llm: BaseChatModel,
    searches: list[dict] | None = None,
) -> RunSummary:
    """Run the full job-search-and-apply pipeline.

    Parameters
    ----------
    llm:
        The LangChain chat model to use for the browser agent.
    searches:
        Override the search list from config.  Defaults to
        ``job_titles.SEARCHES``.

    Returns
    -------
    RunSummary with aggregate stats.
    """
    searches = searches or job_titles.SEARCHES
    summary = RunSummary()
    browser = _build_browser()

    try:
        for search in searches:
            print(f"\n{'='*60}")
            print(f"  Searching: {search['title']} — {search['location']}")
            print(f"{'='*60}\n")

            task = _build_task_prompt(search)

            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                controller=controller,
            )

            history = await agent.run(max_steps=MAX_AGENT_STEPS)

            # Accumulate token usage
            if history.usage:
                u = history.usage
                summary.token_usage.input_tokens += u.total_prompt_tokens
                summary.token_usage.output_tokens += u.total_completion_tokens
                summary.token_usage.cached_tokens += u.total_prompt_cached_tokens
                summary.token_usage.total_tokens += u.total_tokens
                summary.token_usage.total_cost += u.total_cost

            print(f"\n--- Search complete: {search['title']} ---")
            result = history.final_result()
            if result:
                print(f"Agent summary: {result[:500]}")
    finally:
        await browser.stop()

    summary.run_finished = datetime.now().isoformat()

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

    # Save the run summary
    summary_path = save_run_summary(summary)
    print(f"\nRun summary saved to {summary_path}")

    return summary
