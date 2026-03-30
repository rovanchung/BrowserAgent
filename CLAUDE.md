# CLAUDE.md

## Project Overview

BrowserAgent is an autonomous browser automation agent that searches for jobs on LinkedIn (and other boards), evaluates qualifications, generates cover letters, and applies on behalf of a candidate. Built on [browser-use](https://github.com/browser-use/browser-use).

## Architecture

- **Entry point:** `main.py` — interactive menu when run with no args, or CLI flags for scripted use
- **Interactive menu:** `src/utils/interactive.py` — multi-level select menu shown when no flags are passed
- **Orchestration:** `src/agent/job_agent.py` — `run_job_search()` loops through searches, creates an Agent + Browser per search, runs the LLM-driven browser agent
- **Actions:** `src/agent/actions.py` — 8+ custom browser-use actions (read_resume, save_application, check_company, etc.)
- **LLM factory:** `src/agent/llm.py` — builds the right chat model (OpenAI, Anthropic, Google/Vertex, Ollama)
- **Output:** `src/utils/output.py` — JSON/CSV persistence, run summaries, progress tracking for `--resume`
- **Config:** `config/profile.py`, `config/job_titles.py`, `config/settings.py` — user identity, search params, agent behavior
- **Schemas:** `src/models/schemas.py` — Pydantic models for JobListing, ApplicationRecord, RunSummary

## Key Design Decisions

- **LLM-driven navigation:** The agent does NOT explicitly track page numbers or job indices. The LLM decides when to scroll, paginate, and click. LinkedIn `start=N` offset is used for `--resume`.
- **URL-based deduplication:** `load_applied_urls()` reads all previously applied URLs from the log to prevent re-applying.
- **Company skip list:** After each application, the company+title is added to `config/profile.py`'s `companies_to_skip` list (on disk) to prevent re-applying across runs.
- **Progress tracking:** `output/progress.json` saves `search_index` and `listings_reviewed` after every action. Cleared on successful completion. Used by `--resume`.
- **Ctrl+C handling:** SIGINT triggers `os._exit(130)` to bypass Playwright cleanup and keep browser tabs open.
- **Google provider:** Uses `google-genai` SDK (`from google import genai`). Supports both Gemini API (`GOOGLE_API_KEY`) and Vertex AI (`USE_VERTEX_AI=true` + `gcloud auth application-default login`).

## Development Commands

```bash
# Run
python main.py

# Run tests
python -m pytest tests/

# Dry run (no browser, just prints prompts)
python main.py --dry-run
```

## Environment

- Python venv at `.venv/` (Python 3.14)
- Config files are copied from `.example.py` templates
- API keys go in `.env` (not committed)
- `resume/resume.pdf` is required; `resume/resume.txt` is auto-generated

## When Updating

- If you add a new CLI flag, update `main.py`, `src/utils/interactive.py` (the interactive menu), and `README.md`
- If you add a new action, update the Custom Actions table in `README.md`
- If you change config fields, update the Configuration Reference in `README.md`
- If you change LLM provider setup, update Supported LLM Providers in `README.md`
- If you add new output files, update the Project Structure tree and Output section in `README.md`
