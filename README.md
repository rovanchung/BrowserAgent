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

The agent uses your **keyword-to-answer map** in `config/profile.py` to handle screening questions deterministically — no hallucinated answers. When it hits something it can't handle (CAPTCHA, ambiguous question, login wall), it pauses and asks you.

## Project Structure

```
BrowserAgent/
├── main.py                          # Entry point — CLI with flags
├── .env                             # Your API key (create from .env.example)
├── requirements.txt
│
├── config/
│   ├── profile.py                   # Personal info, Q&A auto-answers, skip lists
│   ├── job_titles.py                # Target roles, locations, search filters
│   └── settings.py                  # LLM provider, browser, output settings
│
├── resume/
│   └── resume.md                   # Your resume (plain text)
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
    ├── cover_letters/               # One .txt file per application
    │   └── Acme_Corp_Senior_SWE_20260208_143022.txt
    └── run_20260208_143022.json     # Per-run summary with stats
```

## Prerequisites

- Python 3.11+
- An LLM API key (OpenAI, Anthropic, or Google) **or** a local model via [Ollama](https://ollama.ai)
- A Chrome browser (the agent installs its own Chromium, but your Chrome profile can be reused for saved logins)

## Setup

### Step 1 — Clone and install dependencies

```bash
git clone https://github.com/rovanchung/BrowserAgent.git
cd BrowserAgent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Install the browser engine:

```bash
uvx browser-use install
```

> If `uvx` is not available, run `pip install uv` first, or use `playwright install chromium` as a fallback.

### Step 2 — Set your API key

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```env
# Pick one provider:
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sk-...
```

**Using Anthropic:**
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_API_KEY=sk-ant-...
```

**Using Ollama (free, local):**
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:70b
```
Make sure Ollama is running (`ollama serve`) and you've pulled the model (`ollama pull llama3.1:70b`).

### Step 3 — Add your resume

Replace the placeholder with your actual resume:

```bash
# Paste your plain-text resume into this file:
nano resume/resume.md
```

Tips for the resume file:
- Plain text works best (the agent reads it as-is)
- Include contact info, summary, work experience, education, skills
- No special formatting needed — just clear section headings

### Step 4 — Fill in your profile

Edit `config/profile.py` with your real information:

```python
# ── Personal Information ──────────────────────────────
FIRST_NAME = "Jane"
LAST_NAME = "Doe"
EMAIL = "jane.doe@email.com"
PHONE = "+1-555-012-3456"
LOCATION = "San Francisco, CA"
LINKEDIN_URL = "https://linkedin.com/in/janedoe"
# ...

# ── Experience ────────────────────────────────────────
YEARS_OF_EXPERIENCE = 6
CURRENT_TITLE = "Senior Software Engineer"
SKILLS = ["Python", "TypeScript", "AWS", "Kubernetes", ...]

# ── Screening Question Auto-Answers ──────────────────
# Keyword in question → your answer (first match wins)
QUESTION_ANSWERS = {
    "authorized to work": "Yes",
    "years of experience": "6",
    "willing to relocate": "No",
    "salary expectation": "150,000-200,000 USD",
    # ... add your own
}

# ── Companies to Skip ────────────────────────────────
COMPANIES_TO_SKIP = [
    "Current Employer Inc.",
]
```

The `QUESTION_ANSWERS` dictionary is the most important part — it maps keyword patterns found in screening questions to your answers. The agent checks each question against these keywords (case-insensitive, first match wins) so your answers are always consistent and factual.

### Step 5 — Configure your job searches

Edit `config/job_titles.py`:

```python
SEARCHES = [
    {
        "title": "Senior Software Engineer",
        "location": "San Francisco, CA",
        "remote_only": True,
    },
    {
        "title": "Staff Software Engineer",
        "location": "Remote",
        "remote_only": True,
    },
]

JOB_BOARDS = ["linkedin"]         # Supported: "linkedin", "indeed"
DATE_POSTED = "past_week"          # "past_24h", "past_week", "past_month", "any"
MAX_APPLICATIONS_PER_RUN = 10      # Stop after N successful applications
MIN_SKILL_MATCH_RATIO = 0.3        # 30% of your skills must match the JD
```

### Step 6 — (Recommended) Pre-authenticate in Chrome

The agent works best when you're already logged in to job boards. This avoids login walls and CAPTCHAs:

1. Open Chrome and log in to LinkedIn (or whatever board you're using)
2. Find your Chrome profile path: navigate to `chrome://version` and look for "Profile Path"
3. Add the **parent directory** of that path to `.env`:

```env
# Example (Linux):
CHROME_PROFILE_PATH=/home/you/.config/google-chrome

# Example (macOS):
CHROME_PROFILE_PATH=/Users/you/Library/Application Support/Google/Chrome

# Example (Windows):
CHROME_PROFILE_PATH=C:\Users\you\AppData\Local\Google\Chrome\User Data
```

> Close Chrome before running the agent — Chrome locks its profile to one process at a time.

### Step 7 — Run

```bash
# Normal run (opens visible browser window)
python main.py

# Headless mode (no visible browser)
python main.py --headless

# Override LLM provider/model from the command line
python main.py --provider anthropic --model claude-sonnet-4-5-20250929

# Dry run — prints the task prompts without opening a browser
python main.py --dry-run
```

The agent will:
1. Read your resume and profile
2. Navigate to the job board
3. Run each search from `config/job_titles.py`
4. For each listing: check company block list, check description for blocked keywords, evaluate skill match
5. For qualified jobs: fill the application, answer screening questions, generate a cover letter, submit
6. Log everything to `output/`

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

## Custom Actions

The agent has 8 custom actions beyond standard browser interaction:

| Action | What it does |
|--------|-------------|
| `read_resume` | Loads `resume/resume.md` into the agent's context |
| `get_profile` | Returns structured profile data (name, email, skills, etc.) |
| `answer_screening_question` | Keyword-matches a question to your pre-configured answer |
| `save_application` | Logs a successful application + cover letter to output |
| `save_skipped_job` | Logs a skipped job with the reason (not qualified, blocked, etc.) |
| `check_company` | Checks a company name against your block list |
| `check_job_description` | Scans a JD for blocked keywords (e.g., "security clearance") |
| `ask_human` | Pauses the agent and asks you for help in the terminal |

## Configuration Reference

| File | What to edit | Key fields |
|------|-------------|------------|
| `.env` | API keys, LLM provider | `OPENAI_API_KEY`, `LLM_PROVIDER`, `CHROME_PROFILE_PATH` |
| `config/profile.py` | Your identity | Name, email, phone, skills, education, `QUESTION_ANSWERS`, `COMPANIES_TO_SKIP` |
| `config/job_titles.py` | What to search for | `SEARCHES`, `JOB_BOARDS`, `DATE_POSTED`, `MAX_APPLICATIONS_PER_RUN` |
| `config/settings.py` | Agent behavior | `HEADLESS`, `MAX_AGENT_STEPS`, `GENERATE_COVER_LETTER`, `OUTPUT_FORMAT` |
| `resume/resume.md` | Your resume | Plain text, no formatting required |

## Supported LLM Providers

| Provider | Model examples | Install |
|----------|---------------|---------|
| OpenAI | `gpt-4.1`, `gpt-4.1-mini` | `pip install langchain-openai` |
| Anthropic | `claude-sonnet-4-5-20250929` | `pip install langchain-anthropic` |
| Google | `gemini-2.5-flash` | `pip install langchain-google-genai` |
| Ollama (local) | `llama3.1:70b`, `qwen2.5:7b` | `pip install langchain-ollama` |

The default `requirements.txt` installs OpenAI and Anthropic. Uncomment the others if needed.

## Tips

- **Start with `--dry-run`** to see the exact prompts the agent will use before spending API credits
- **Watch the first run** with the browser visible (`HEADLESS = False`) to see how the agent navigates and catch any issues
- **Keep `MIN_SKILL_MATCH_RATIO` low** (0.2-0.3) if you want more applications, raise it (0.5+) to be selective
- **Add more `QUESTION_ANSWERS`** as you discover new screening questions — the more you add, the fewer times the agent has to guess
- **Use a Chrome profile** with saved logins to avoid authentication issues entirely
- **Local models** (Ollama) work but have noticeably lower success rates on complex multi-page forms — use 70B+ parameter models for best results

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Resume file not found` | Create `resume/resume.md` with your resume text |
| Browser won't start | Run `uvx browser-use install` to install Chromium |
| Login wall on LinkedIn | Set `CHROME_PROFILE_PATH` in `.env` to your logged-in Chrome profile |
| CAPTCHA appears | The agent will call `ask_human` — solve it manually and press Enter |
| Agent loops or gets stuck | Lower `MAX_AGENT_STEPS` in `config/settings.py`, or try a stronger model |
| `ModuleNotFoundError` for a provider | Install the missing provider: `pip install langchain-ollama` (etc.) |
| Chrome profile locked | Close all Chrome windows before running — Chrome locks its profile dir |
