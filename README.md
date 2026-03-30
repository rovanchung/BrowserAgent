# BrowserAgent

An autonomous browser agent that searches for jobs, evaluates whether you're qualified, generates tailored cover letters, and applies on your behalf. You configure your profile, resume, and target roles once — the agent handles the rest.

Built on [Browser Use](https://github.com/browser-use/browser-use), an open-source AI browser automation framework that combines DOM extraction with visual understanding to navigate real websites.

## How It Works

```
You fill in config files (profile, resume, job titles)
    |
    v
Agent opens a real browser and navigates to job boards
    |
    v
For each search: finds listings → reads descriptions → checks qualifications
    |
    v
Qualified jobs: fills application forms, answers screening questions,
generates a cover letter, uploads resume, submits
    |
    v
Everything logged to output/ (JSON/CSV + individual cover letter files)
```

The agent reads your **profile dictionary** in `config/profile.py` and uses it — along with your resume — to answer screening questions. When it hits something it can't handle (CAPTCHA, ambiguous question, login wall), it pauses and asks you.

## Project Structure

```
BrowserAgent/
├── main.py                          # Entry point — CLI with flags
├── .env                             # Your API key (create from .env.example)
├── requirements.txt
│
├── config/
│   ├── profile.example.py           # Template — copy to profile.py and fill in
│   ├── job_titles.example.py        # Template — copy to job_titles.py and customize
│   └── settings.example.py          # Template — copy to settings.py and adjust
│
├── resume/
│   └── resume.pdf                  # Your resume (PDF — text extracted automatically)
│
├── src/
│   ├── agent/
│   │   ├── actions.py               # 8 custom actions the agent can call
│   │   ├── job_agent.py             # Orchestrator: search → filter → apply
│   │   └── llm.py                   # LLM factory (OpenAI/Anthropic/Google/Ollama)
│   ├── models/
│   │   └── schemas.py               # Pydantic models for all structured data
│   └── utils/
│       ├── cover_letter.py          # LLM-powered cover letter generation
│       └── output.py                # JSON/CSV persistence + dedup
│
└── output/                          # Created automatically on first run
    ├── applications.json            # Rolling log of all applications
    ├── applications.csv             # (if CSV mode enabled)
    ├── progress.json                # Resume checkpoint (auto-cleared on completion)
    ├── cover_letters/               # One .txt file per application
    │   └── Acme_Corp_Senior_SWE_20260208_143022.txt
    └── run_20260208_143022.json     # Per-run summary with stats
```

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

The script walks you through every step: creating a virtual environment, installing dependencies, configuring your LLM provider and API key, copying config templates, and importing your resume. Each prompt explains what the value is for and where it's stored.

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
    "cover_letter": "Having led the migration of Acme's payment...",
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
    "cover_letter": "",
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

**`run_<timestamp>.json`** — per-run summary with aggregate stats.

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

The agent has 8 custom actions beyond standard browser interaction:

| Action | What it does |
|--------|-------------|
| `read_resume` | Loads the resume text (auto-extracted from `resume/resume.pdf`) into the agent's context |
| `get_profile` | Returns the full `PROFILE` dictionary as JSON |
| `answer_screening_question` | Returns the profile and resume so the agent can answer any screening question |
| `save_application` | Logs a successful application + cover letter to output |
| `save_skipped_job` | Logs a skipped job with the reason (not qualified, blocked, etc.) |
| `check_company` | Checks a company name against your block list |
| `check_job_description` | Scans a JD for blocked keywords (e.g., "security clearance") |
| `ask_human` | Pauses the agent and asks you for help in the terminal |

## Configuration Reference

| File | What to edit | Key fields |
|------|-------------|------------|
| `.env` | API keys, LLM provider | `OPENAI_API_KEY`, `LLM_PROVIDER`, `CHROME_PROFILE_PATH`, `GCP_PROJECT` |
| `config/profile.py` | Your identity (copy from `profile.example.py`) | `PROFILE` dict: name, email, phone, skills, education, `companies_to_skip`, `keywords_to_avoid` |
| `config/job_titles.py` | What to search for (copy from `job_titles.example.py`) | `SEARCHES`, `JOB_BOARDS`, `DATE_POSTED`, `MAX_APPLICATIONS_PER_RUN` |
| `config/settings.py` | Agent behavior (copy from `settings.example.py`) | `HEADLESS`, `MAX_AGENT_STEPS`, `GENERATE_COVER_LETTER`, `OUTPUT_FORMAT` |
| `resume/resume.pdf` | Your resume | PDF format — plain text is extracted automatically on startup |

## Supported LLM Providers

| Provider | Model examples | Install |
|----------|---------------|---------|
| OpenAI | `gpt-4.1`, `gpt-4.1-mini` | `pip install langchain-openai` |
| Anthropic | `claude-sonnet-4-5-20250929` | `pip install langchain-anthropic` |
| Google | `gemini-2.5-flash`, `gemini-3-flash-preview` | Gemini API (default) or Vertex AI (`USE_VERTEX_AI=true` + `GCP_PROJECT` in `.env`) |
| Ollama (local) | `llama3.1:70b`, `qwen2.5:7b` | `pip install langchain-ollama` |

The default `requirements.txt` installs OpenAI and Anthropic. Uncomment the others if needed.

## Tips

- **First run?** Just run `python main.py` — the interactive menu guides you through everything
- **Watch the first run** with the browser visible to see how the agent navigates and catch any issues
- **Keep `MIN_SKILL_MATCH_RATIO` low** (0.2-0.3) if you want more applications, raise it (0.5+) to be selective
- **Fill in your profile thoroughly** — the more data the agent has, the better it answers screening questions
- **Use a Chrome profile** with saved logins to avoid authentication issues entirely
- **Local models** (Ollama) work but have noticeably lower success rates on complex multi-page forms — use 70B+ parameter models for best results

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
| Interrupted mid-run | Press Ctrl+C (browser tabs stay open), then run `python main.py` again — the menu will offer to resume |
