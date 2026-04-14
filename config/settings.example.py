"""
General settings for the browser agent.

Configure your LLM provider, browser behavior, and output preferences.
API keys should go in .env (not here).
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESUME_PDF_PATH = PROJECT_ROOT / "resume" / "resume.pdf"
RESUME_PATH = PROJECT_ROOT / "resume" / "resume.txt"  # auto-generated from PDF
OUTPUT_DIR = PROJECT_ROOT / "output"

# ── LLM Configuration ───────────────────────────────────────────────
# Provider: "openai", "anthropic", "google", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Model name (varies by provider)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")

# For Ollama / local models
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── Google Vertex AI ────────────────────────────────────────────────
# Set USE_VERTEX_AI=true to use Vertex AI instead of the Gemini API.
USE_VERTEX_AI = os.getenv("USE_VERTEX_AI", "false").lower() == "true"
GCP_PROJECT = os.getenv("GCP_PROJECT", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-west1")

# Temperature for LLM calls (lower = more deterministic)
LLM_TEMPERATURE = 0.3

# ── Browser Configuration ────────────────────────────────────────────
# Path to an existing Chrome user-data directory.
# Using a real profile lets you skip login — pre-authenticate in Chrome first.
# Leave empty to use a fresh browser session each run.
CHROME_PROFILE_PATH = os.getenv("CHROME_PROFILE_PATH", "")

# Run browser in headless mode (no visible window).
# Set to False to watch the agent work.
HEADLESS = False

# Max number of agent steps before the agent gives up on a single task.
MAX_AGENT_STEPS = 50

# Seconds to wait for a single LLM call before timing out.
# browser-use defaults to 60-90s depending on the model; increase for large contexts.
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))

# Seconds to wait between actions (helps avoid bot detection).
ACTION_DELAY = 1.0

# ── Cover Letter ─────────────────────────────────────────────────────
# Cover letter mode: "ai" = generate with LLM, "generic" = use saved
# cover_letter.pdf from resume/, "none" = skip cover letters.
COVER_LETTER_MODE = os.getenv("COVER_LETTER_MODE", "ai")

# Path to the generic cover letter text (auto-generated from cover_letter.pdf on startup).
COVER_LETTER_PATH = PROJECT_ROOT / "resume" / "cover_letter.txt"
COVER_LETTER_PDF_PATH = PROJECT_ROOT / "resume" / "cover_letter.pdf"

# ── Skip-list matching ─────────────────────────────────────────────
# Max Levenshtein edit-distance allowed when matching job titles /
# company names against the skip list.  0 = exact substring only.
SKIP_MATCH_TOLERANCE = int(os.getenv("SKIP_MATCH_TOLERANCE", "0"))

# ── Output ───────────────────────────────────────────────────────────
# Format for the application tracking log.
# "json" = one JSON file with all applications
# "csv"  = one CSV file
OUTPUT_FORMAT = "json"
