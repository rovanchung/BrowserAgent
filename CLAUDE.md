# CLAUDE.md

## Project Overview

BrowserAgent is an autonomous browser automation agent that searches for jobs on LinkedIn (and other boards), evaluates qualifications, generates cover letters, and applies on behalf of a candidate. Built on [browser-use](https://github.com/browser-use/browser-use).

## Architecture

- **Entry point:** `main.py` — interactive menu when run with no args, or CLI flags for scripted use. Registers signal handlers (SIGINT for Ctrl+C exit, SIGTSTP for Ctrl+Z pause/resume). Validates config files and auto-generates `resume/resume.txt` from PDF on startup.
- **Interactive menu:** `src/utils/interactive.py` — multi-level arrow-key select menu shown when no flags are passed. Level 1: mode (Search & Apply / Apply to URL / Dry Run). Level 2: mode-specific inputs + options multi-select. Level 3: LLM override.
- **Orchestration:** `src/agent/job_agent.py` — `run_job_search()` loops through searches, creates an Agent + Browser per search, runs the LLM-driven browser agent. `run_single_apply()` handles single-URL mode. Builds LinkedIn search URLs with query params (keywords, location, date, experience level, remote, pagination offset).
- **Actions:** `src/agent/actions.py` — 11 custom browser-use actions (read_resume, get_resume_file_path, get_profile, answer_screening_question, save_application, save_skipped_job, check_company, check_job_description, ask_human, make_cover_letter, upload_cover_letter). Includes fuzzy matching helpers (`_levenshtein`, `_fuzzy_contains`) for company skip list.
- **LLM factory:** `src/agent/llm.py` — `build_llm()` returns the right chat model (OpenAI, Anthropic, Google/Vertex, Ollama) based on config
- **Output:** `src/utils/output.py` — JSON/CSV persistence, run summaries, progress tracking for `--resume`, token cost accumulation via `config/pricing.py`
- **Cover letters:** `src/utils/cover_letter.py` — async LLM-based generation using system prompt from `config/cover_letter_prompt.py`
- **PDF extraction:** `src/utils/pdf_to_text.py` — converts `resume.pdf` to plain text via PyMuPDF
- **Pause gate:** `src/utils/pause.py` — Ctrl+Z toggle handler, `wait_if_paused()` blocking gate
- **Config:** `config/profile.py`, `config/job_titles.py`, `config/settings.py` — user identity, search params, agent behavior
- **Config (non-template):** `config/cover_letter_prompt.py` (system prompt), `config/pricing.py` (token cost table)
- **Schemas:** `src/models/schemas.py` — Pydantic models: JobListing, ApplicationRecord, TokenUsage, RunSummary. Enums: ApplicationStatus, SkipReason.
- **Tests:** `tests/test_fuzzy_matching.py` — unit tests for Levenshtein distance, fuzzy contains, and check_company action

## Key Design Decisions

- **LLM-driven navigation:** The agent does NOT explicitly track page numbers or job indices. The LLM decides when to scroll, paginate, and click. LinkedIn `start=N` offset is used for `--resume`.
- **URL-based deduplication:** `load_applied_urls()` reads all previously applied URLs from JSON + CSV logs to prevent re-applying.
- **Company skip list:** After each application, the company+title is added to `config/profile.py`'s `companies_to_skip` list (on disk) to prevent re-applying across runs. Supports fuzzy matching with configurable tolerance.
- **Skip list format:** `"*:CompanyName"` blocks all jobs at a company. `"Job Title:CompanyName"` blocks a specific title. Fuzzy matching uses Levenshtein distance with `SKIP_MATCH_TOLERANCE` (default 0 = exact).
- **Progress tracking:** `output/progress.json` saves `search_index` and `listings_reviewed` after every action. Cleared on successful completion. Used by `--resume`.
- **Ctrl+C handling:** SIGINT triggers `os._exit(130)` to bypass Playwright cleanup and keep browser tabs open.
- **Ctrl+Z handling:** SIGTSTP toggles pause state via `src/utils/pause.py`. Agent finishes current action then blocks.
- **Google provider:** Uses `ChatGoogle` from `browser_use.llm.google`. Supports both Gemini API (`GOOGLE_API_KEY`) and Vertex AI (`USE_VERTEX_AI=true` + `gcloud auth application-default login`).
- **Cover letter generation:** Uses same LLM as browser agent. System prompt in `config/cover_letter_prompt.py` emphasizes natural tone (no buzzwords). Text is pasted into form text fields; if only a file upload is available, `upload_cover_letter` uploads `resume/cover_letter.pdf` directly via CDP. `cover_letter.txt` is auto-generated from `cover_letter.pdf` on startup.
- **Token cost tracking:** `config/pricing.py` has per-model pricing. `output.py` accumulates costs across agent steps. Run summaries include total cost.
- **One browser per search:** Each search query gets a fresh Browser + Agent instance to avoid state leakage.

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
- `resume/resume.pdf` is required; `resume/resume.txt` is auto-generated from PDF on startup
- `resume/cover_letter.pdf` is optional; if present, `resume/cover_letter.txt` is auto-generated from it on startup

## When Updating

Any user-facing change (new CLI flag, action, config field, LLM provider, or output file) must be reflected in the corresponding source files **and** their matching `README.md` sections (CLI Flags, Custom Actions, Configuration Reference, Supported LLM Providers, Project Structure/Output).
