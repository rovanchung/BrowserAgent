"""
Output manager — persists application records to disk.

Supports JSON and CSV formats. Each run appends to a single
rolling log file so you never lose historical data.

The module also holds the *active* ``RunSummary`` for the current
run so that agent actions can update it in real-time and flush
incremental state to disk after every meaningful event.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from config.pricing import get_token_cost
from config.settings import LLM_MODEL, LLM_PROVIDER, OUTPUT_DIR, OUTPUT_FORMAT
from src.models.schemas import ApplicationRecord, ApplicationStatus, RunSummary

# ── Runtime context (active run) ────────────────────────────────────

_current_summary: RunSummary | None = None
_current_summary_path: Path | None = None


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


# ── JSON output ──────────────────────────────────────────────────────


def _json_path() -> Path:
    return _ensure_output_dir() / "applications.json"


def _load_json_log() -> list[dict]:
    path = _json_path()
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_json_log(records: list[dict]) -> None:
    _json_path().write_text(json.dumps(records, indent=2, ensure_ascii=False))


def save_record_json(record: ApplicationRecord) -> None:
    records = _load_json_log()
    records.append(json.loads(record.model_dump_json()))
    _save_json_log(records)


# ── CSV output ───────────────────────────────────────────────────────

_CSV_COLUMNS = [
    "applied_at",
    "status",
    "skip_reason",
    "title",
    "company",
    "location",
    "url",
    "salary_range",
    "job_board",
    "search_query",
    "screening_answers",
    "notes",
]


def _csv_path() -> Path:
    return _ensure_output_dir() / "applications.csv"


def save_record_csv(record: ApplicationRecord) -> None:
    path = _csv_path()
    write_header = not path.exists()

    row = {
        "applied_at": record.applied_at,
        "status": record.status.value,
        "skip_reason": record.skip_reason.value if record.skip_reason else "",
        "title": record.job.title,
        "company": record.job.company,
        "location": record.job.location,
        "url": record.job.url,
        "salary_range": record.job.salary_range,
        "job_board": record.job.job_board,
        "search_query": record.job.search_query,
        "screening_answers": json.dumps(record.screening_answers, ensure_ascii=False),
        "notes": record.notes,
    }

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ── Public API ───────────────────────────────────────────────────────


def save_record(record: ApplicationRecord) -> Path:
    """Save an application record using the configured output format."""
    if OUTPUT_FORMAT == "csv":
        save_record_csv(record)
        return _csv_path()
    else:
        save_record_json(record)
        return _json_path()


def _find_cover_letter(answers: dict[str, str]) -> str:
    """Extract the cover letter value from screening_answers, if present."""
    for key, value in answers.items():
        if "cover letter" in key.lower():
            return value
    return ""


def save_cover_letter_file(record: ApplicationRecord) -> Path | None:
    """Save a cover letter as a standalone text file alongside the log."""
    cover_letter = _find_cover_letter(record.screening_answers)
    if not cover_letter:
        return None

    cl_dir = _ensure_output_dir() / "cover_letters"
    cl_dir.mkdir(exist_ok=True)

    safe_company = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in record.job.company
    )
    safe_title = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in record.job.title
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_company}_{safe_title}_{timestamp}.txt"

    path = cl_dir / filename
    path.write_text(cover_letter, encoding="utf-8")
    return path


def save_run_summary(summary: RunSummary) -> Path:
    """Save the full run summary (includes all application records)."""
    path = _ensure_output_dir() / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return path


# ── Incremental run-summary management ──────────────────────────────


def init_run_summary() -> RunSummary:
    """Create a new ``RunSummary``, persist the initial state, and return it."""
    global _current_summary, _current_summary_path
    _current_summary = RunSummary()
    _current_summary_path = (
        _ensure_output_dir() / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    flush_run_summary()
    return _current_summary


def get_run_summary() -> RunSummary | None:
    """Return the active ``RunSummary`` (or *None* outside a run)."""
    return _current_summary


def flush_run_summary() -> Path | None:
    """Write the current run summary to disk (incremental save)."""
    if _current_summary is None or _current_summary_path is None:
        return None
    _current_summary_path.write_text(
        _current_summary.model_dump_json(indent=2), encoding="utf-8"
    )
    return _current_summary_path


def accumulate_tokens(usage: object) -> None:
    """Add token counts from a browser-use history usage object.

    Flushes the updated summary to disk so the output file always
    reflects the latest token totals.
    """
    if _current_summary is None or usage is None:
        return
    input_toks = usage.total_prompt_tokens
    output_toks = usage.total_completion_tokens
    cached_toks = usage.total_prompt_cached_tokens
    _current_summary.token_usage.input_tokens += input_toks
    _current_summary.token_usage.output_tokens += output_toks
    _current_summary.token_usage.cached_tokens += cached_toks
    _current_summary.token_usage.total_tokens += usage.total_tokens
    _current_summary.token_usage.total_cost += get_token_cost(
        LLM_PROVIDER, LLM_MODEL, input_toks, output_toks, cached_toks
    )
    flush_run_summary()


def finalize_run_summary() -> Path:
    """Mark the run finished and perform the final flush.

    Returns the path to the saved file and clears the module-level
    state so a fresh run can start later.
    """
    global _current_summary, _current_summary_path
    if _current_summary is None or _current_summary_path is None:
        raise RuntimeError("No active run summary to finalize")
    _current_summary.run_finished = datetime.now().isoformat()
    flush_run_summary()
    path = _current_summary_path
    _current_summary = None
    _current_summary_path = None
    return path


def load_applied_urls() -> set[str]:
    """Return all URLs that have been applied to (or attempted) in past runs."""
    urls: set[str] = set()

    # From JSON log
    json_path = _json_path()
    if json_path.exists():
        for rec in json.loads(json_path.read_text()):
            job = rec.get("job", {})
            if job.get("url"):
                urls.add(job["url"])

    # From CSV log
    csv_path = _csv_path()
    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("url"):
                    urls.add(row["url"])

    return urls


# ── Progress tracking (for --resume) ──────────────────────────────


def _progress_path() -> Path:
    return _ensure_output_dir() / "progress.json"


def load_progress() -> dict:
    """Load saved progress from the last interrupted run.

    Returns a dict with:
        search_index: index of the search that was in progress (0-based)
        listings_reviewed: number of listings reviewed in that search
    """
    path = _progress_path()
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_progress(search_index: int, listings_reviewed: int) -> None:
    """Save current progress so it can be resumed later."""
    data = {
        "search_index": search_index,
        "listings_reviewed": listings_reviewed,
        "saved_at": datetime.now().isoformat(),
    }
    _progress_path().write_text(json.dumps(data, indent=2))


def clear_progress() -> None:
    """Remove the progress file after a successful run completes."""
    path = _progress_path()
    if path.exists():
        path.unlink()
