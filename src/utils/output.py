"""
Output manager — persists application records to disk.

Supports JSON and CSV formats. Each run appends to a single
rolling log file so you never lose historical data.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from config.settings import OUTPUT_DIR, OUTPUT_FORMAT
from src.models.schemas import ApplicationRecord, ApplicationStatus, RunSummary


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
    "cover_letter",
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
        "cover_letter": record.cover_letter.replace("\n", "\\n"),
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


def save_cover_letter(record: ApplicationRecord) -> Path | None:
    """Save a cover letter as a standalone text file alongside the log."""
    if not record.cover_letter:
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
    path.write_text(record.cover_letter, encoding="utf-8")
    return path


def save_run_summary(summary: RunSummary) -> Path:
    """Save the full run summary (includes all application records)."""
    path = _ensure_output_dir() / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
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
