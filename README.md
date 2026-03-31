# BrowserAgent

An autonomous browser agent that searches for jobs, evaluates whether you're qualified, generates tailored cover letters, and applies on your behalf. You configure your profile, resume, and target roles once — the agent handles the rest.

Built on [Browser Use](https://github.com/browser-use/browser-use), an open-source AI browser automation framework that combines DOM extraction with visual understanding to navigate real websites.

## How It Works

1. **You configure** your profile, resume, and target job titles in a few config files.
2. **The agent opens a real browser**, navigates to LinkedIn (or other job boards), and searches for your target roles.
3. **For each listing**, it reads the job description, checks your skills against the requirements, and skips jobs that don't match (or hit your block list).
4. **For qualified jobs**, it fills out the application form, answers screening questions using your profile, generates a cover letter, uploads your resume, and submits.
5. **Everything is logged** to `output/` — a JSON/CSV record of every application, individual cover letter files, and a per-run summary with token costs.

If the agent hits something it can't handle (CAPTCHA, ambiguous question, login wall), it pauses and asks you in the terminal.

## Prerequisites

- Python 3.11+
- An LLM API key (OpenAI, Anthropic, or Google) **or** a local model via [Ollama](https://ollama.ai)
- A Chrome browser (the agent installs its own Chromium, but your Chrome profile can be reused for saved logins)

## Setup

Run the interactive setup wizard:

```bash
git clone https://github.com/rovanchung/BrowserAgent.git
cd BrowserAgent
bash setup.sh
```

The script walks you through every step: creating a virtual environment, installing dependencies, installing the browser engine, configuring your LLM provider and API key, copying config templates, and importing your resume. Each prompt explains what the value is for and where it's stored.

> **Prefer manual setup?** See the [Configuration Reference](#configuration-reference) below — the files you need are `.env` (from `.env.example`), `config/profile.py`, `config/job_titles.py`, and `config/settings.py` (each from their `.example.py` template), plus your resume at `resume/resume.pdf`.

### Run

```bash
# Interactive menu — walks you through all options
python main.py

# Or pass flags directly to skip the menu
python main.py --initial-actions --review
python main.py --url https://linkedin.com/jobs/view/123456
python main.py --dry-run
```

Run `python main.py --help` for the full list of flags.

### CLI Flags

| Flag | Description |
|------|-------------|
| `--provider {openai,anthropic,google,ollama}` | Override LLM provider from `.env` |
| `--model MODEL` | Override model name from `.env` |
| `--headless` | Run browser without a visible window |
| `--url URL` | Apply directly to a single job posting (skips search) |
| `--dry-run` | Print task prompts without launching the browser |
| `--initial-actions` | Navigate via URL params instead of LLM search steps (saves tokens) |
| `--review` | Pause for human approval before submitting each application |
| `--keep-alive` | Keep browser open after the agent finishes |
| `--resume` | Resume from last interrupted run's progress |

## Output

After a run, check the `output/` directory:

**`applications.json`** — rolling log of every application attempt:
```json
[
  {
    "job": {
      "title": "Senior Software Engineer",
      "company": "Acme Corp",
      "location": "Remote",
      "url": "https://linkedin.com/jobs/view/123456",
      "job_board": "linkedin",
      "search_query": "Senior Software Engineer in Remote"
    },
    "status": "applied",
    "skip_reason": null,
    "screening_answers": {"Cover Letter": "Having led the migration..."},
    "applied_at": "2026-02-08T14:30:22.123456",
    "notes": ""
  },
  {
    "job": {
      "title": "Security Engineer",
      "company": "DefenseTech",
      "url": "https://linkedin.com/jobs/view/789012"
    },
    "status": "skipped",
    "skip_reason": "keyword_blocked",
    "applied_at": "2026-02-08T14:32:05.654321",
    "notes": ""
  }
]
```

**`cover_letters/`** — individual files per application:
```
output/cover_letters/
├── Acme_Corp_Senior_Software_Engineer_20260208_143022.txt
├── StartupXYZ_Backend_Engineer_20260208_144511.txt
└── BigCo_Staff_Engineer_20260208_150230.txt
```

**`run_<timestamp>.json`** — per-run summary with aggregate stats and token usage/cost.

The agent also deduplicates across runs — if a job URL already appears in the log, it won't apply again.

**`progress.json`** — resume checkpoint (only exists during an incomplete run):
```json
{
  "search_index": 1,
  "listings_reviewed": 12,
  "saved_at": "2026-02-08T14:35:00.123456"
}
```
Use `--resume` to pick up from where you left off. The file is automatically deleted when a run completes successfully.

## Custom Actions

The agent has 10 custom actions beyond standard browser interaction:

| Action | What it does |
|--------|-------------|
| `read_resume` | Loads the resume text (auto-extracted from `resume/resume.pdf`) into the agent's context |
| `get_resume_file_path` | Returns the absolute path to `resume.pdf` for file upload actions |
| `get_profile` | Returns the full `PROFILE` dictionary as JSON |
| `answer_screening_question` | Returns the profile and resume so the agent can answer any screening question |
| `save_application` | Logs a successful application + screening answers to output |
| `save_skipped_job` | Logs a skipped job with the reason (not qualified, blocked, etc.) |
| `check_company` | Checks a company + job title against your skip list (supports fuzzy matching) |
| `check_job_description` | Scans a JD for blocked keywords (e.g., "security clearance") |
| `ask_human` | Pauses the agent and asks you for help in the terminal |
| `make_cover_letter` | Generates a tailored cover letter using the LLM and saves it to `output/cover_letters/` |

## Configuration Reference

| File | What to edit | Key fields |
|------|-------------|------------|
| `.env` | API keys, LLM provider | `OPENAI_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `CHROME_PROFILE_PATH`, `USE_VERTEX_AI`, `GCP_PROJECT` |
| `config/profile.py` | Your identity (copy from `profile.example.py`) | `PROFILE` dict: name, email, phone, work authorization, education, skills, experience, salary, preferences, `companies_to_skip`, `keywords_to_avoid` |
| `config/job_titles.py` | What to search for (copy from `job_titles.example.py`) | `SEARCHES`, `JOB_BOARDS`, `DATE_POSTED`, `EXPERIENCE_LEVEL`, `MAX_APPLICATIONS_PER_RUN`, `MAX_LISTINGS_TO_REVIEW`, `MIN_SKILL_MATCH_RATIO`, `REQUIRED_KEYWORDS` |
| `config/settings.py` | Agent behavior (copy from `settings.example.py`) | `HEADLESS`, `MAX_AGENT_STEPS`, `LLM_TEMPERATURE`, `ACTION_DELAY`, `GENERATE_COVER_LETTER`, `OUTPUT_FORMAT` |
| `config/cover_letter_prompt.py` | Cover letter system prompt | Tone, length, structure guidelines for generated cover letters |
| `config/pricing.py` | Token cost lookup | Per-model pricing for cost tracking in run summaries |
| `resume/resume.pdf` | Your resume | PDF format — plain text is extracted automatically on startup |

## Supported LLM Providers

| Provider | Model examples | Install |
|----------|---------------|---------|
| OpenAI | `gpt-4.1`, `gpt-4.1-mini` | `pip install langchain-openai` |
| Anthropic | `claude-sonnet-4-5-20250929` | `pip install langchain-anthropic` |
| Google | `gemini-2.5-flash`, `gemini-3-flash-preview` | Gemini API (default) or Vertex AI (`USE_VERTEX_AI=true` + `GCP_PROJECT` in `.env`) |
| Ollama (local) | `llama3.1:70b`, `qwen2.5:7b` | `pip install langchain-ollama` |

The default `requirements.txt` installs OpenAI, Anthropic, and Google. Uncomment Ollama if needed.

## Tips

- **First run?** Just run `python main.py` — the interactive menu guides you through everything
- **Watch the first run** with the browser visible to see how the agent navigates and catch any issues
- **Keep `MIN_SKILL_MATCH_RATIO` low** (0.2-0.3) if you want more applications, raise it (0.5+) to be selective
- **Fill in your profile thoroughly** — the more data the agent has, the better it answers screening questions
- **Use a Chrome profile** with saved logins to avoid authentication issues entirely
- **Local models** (Ollama) work but have noticeably lower success rates on complex multi-page forms — use 70B+ parameter models for best results
- **Company skip list** supports fuzzy matching — after each application, the company+title is auto-added to prevent re-applying across runs

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Z` | Pause/resume the agent — the agent finishes its current action, then waits until you press `Ctrl+Z` again |
| `Ctrl+C` | Quit immediately — browser tabs stay open so you can inspect the page; resume later with `--resume` |

## Project Structure

```
BrowserAgent/
├── main.py                          # Entry point — CLI with flags or interactive menu
├── setup.sh                         # Interactive setup wizard (6-step)
├── .env                             # Your API key (create from .env.example)
├── requirements.txt
│
├── config/
│   ├── profile.example.py           # Template — copy to profile.py and fill in
│   ├── job_titles.example.py        # Template — copy to job_titles.py and customize
│   ├── settings.example.py          # Template — copy to settings.py and adjust
│   ├── cover_letter_prompt.py       # System prompt for cover letter generation
│   └── pricing.py                   # API token pricing table for cost tracking
│
├── resume/
│   └── resume.pdf                   # Your resume (PDF — text extracted automatically)
│
├── src/
│   ├── agent/
│   │   ├── actions.py               # 10 custom actions the agent can call
│   │   ├── job_agent.py             # Orchestrator: search → filter → apply
│   │   └── llm.py                   # LLM factory (OpenAI/Anthropic/Google/Ollama)
│   ├── models/
│   │   └── schemas.py               # Pydantic models for all structured data
│   └── utils/
│       ├── cover_letter.py          # LLM-powered cover letter generation
│       ├── interactive.py           # Arrow-key CLI menu (shown when no flags passed)
│       ├── output.py                # JSON/CSV persistence + dedup + token tracking
│       ├── pause.py                 # Ctrl+Z pause/resume gate
│       └── pdf_to_text.py           # Resume PDF → plain text extraction (PyMuPDF)
│
├── tests/
│   └── test_fuzzy_matching.py       # Unit tests for fuzzy matching & company skip list
│
└── output/                          # Created automatically on first run
    ├── applications.json            # Rolling log of all applications
    ├── applications.csv             # (if CSV mode enabled)
    ├── progress.json                # Resume checkpoint (auto-cleared on completion)
    ├── cover_letters/               # One .txt file per application
    │   └── Acme_Corp_Senior_SWE_20260208_143022.txt
    └── run_20260208_143022.json     # Per-run summary with stats + token costs
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Resume PDF not found` | Place your `resume.pdf` in the `resume/` folder |
| Browser won't start | Run `uvx browser-use install` to install Chromium |
| Login wall on LinkedIn | Set `CHROME_PROFILE_PATH` in `.env` to your logged-in Chrome profile |
| CAPTCHA appears | The agent will call `ask_human` — solve it manually and press Enter |
| `ModuleNotFoundError: config.profile` | Run `cp config/profile.example.py config/profile.py` (and same for the other config files) |
| Agent loops or gets stuck | Lower `MAX_AGENT_STEPS` in `config/settings.py`, or try a stronger model |
| `ModuleNotFoundError` for a provider | Install the missing provider: `pip install langchain-ollama` (etc.) |
| Chrome profile locked | Close all Chrome windows before running — Chrome locks its profile dir |
| Want to pause temporarily | Press `Ctrl+Z` to pause; press `Ctrl+Z` again to resume |
| Interrupted mid-run | Press `Ctrl+C` (browser tabs stay open), then run `python main.py` again — the menu will offer to resume |
