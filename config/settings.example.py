"""
General settings for the browser agent.

Configure your LLM provider, browser behavior, and output preferences.
API keys should go in .env (not here).
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESUME_PATH = PROJECT_ROOT / "resume" / "resume.md"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ── LLM Configuration ───────────────────────────────────────────────
# Provider: "openai", "anthropic", "google", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Model name (varies by provider)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")

# For Ollama / local models
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

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

# Seconds to wait between actions (helps avoid bot detection).
ACTION_DELAY = 1.0

# ── Cover Letter ─────────────────────────────────────────────────────
# Whether to generate a cover letter for each application.
GENERATE_COVER_LETTER = True

# ── Output ───────────────────────────────────────────────────────────
# Format for the application tracking log.
# "json" = one JSON file with all applications
# "csv"  = one CSV file
OUTPUT_FORMAT = "json"
