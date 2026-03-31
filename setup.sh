#!/usr/bin/env bash
set -euo pipefail

# ─── Colors & Helpers ──────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✔${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
error()   { echo -e "${RED}✖${NC}  $*"; }
header()  { echo -e "\n${BOLD}${CYAN}── $* ──${NC}\n"; }
dim()     { echo -e "${DIM}$*${NC}"; }

ask_yn() {
    # ask_yn "prompt" default(y/n)
    local prompt="$1" default="${2:-y}"
    local yn_hint
    if [[ "$default" == "y" ]]; then yn_hint="Y/n"; else yn_hint="y/N"; fi
    while true; do
        echo -en "${YELLOW}?${NC}  ${prompt} [${yn_hint}]: "
        read -r reply
        reply="${reply:-$default}"
        case "$reply" in
            [Yy]*) return 0 ;;
            [Nn]*) return 1 ;;
            *) echo "  Please answer y or n." ;;
        esac
    done
}

ask_input() {
    # ask_input "prompt" "default"
    local prompt="$1" default="${2:-}"
    if [[ -n "$default" ]]; then
        echo -en "${YELLOW}?${NC}  ${prompt} ${DIM}[${default}]${NC}: "
    else
        echo -en "${YELLOW}?${NC}  ${prompt}: "
    fi
    read -r reply
    echo "${reply:-$default}"
}

ask_choice() {
    # ask_choice "prompt" "opt1" "opt2" ...
    local prompt="$1"; shift
    local options=("$@")
    echo -e "${YELLOW}?${NC}  ${prompt}"
    for i in "${!options[@]}"; do
        echo -e "   ${BOLD}$((i+1)))${NC} ${options[$i]}"
    done
    while true; do
        echo -en "   ${DIM}Enter number [1]:${NC} "
        read -r choice
        choice="${choice:-1}"
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
            echo "${options[$((choice-1))]}"
            return
        fi
        echo "   Please enter a number between 1 and ${#options[@]}."
    done
}

# ─── Preamble ──────────────────────────────────────────────────────────

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║        BrowserAgent — Setup Wizard       ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
dim "This script will walk you through the initial setup."
dim "It creates config files, installs dependencies, and"
dim "asks for the details the agent needs to run."
echo ""

# ─── Step 1: Python venv ──────────────────────────────────────────────

header "Step 1 / 6 — Python virtual environment"

if [[ -d ".venv" ]]; then
    success "Virtual environment already exists at ${BOLD}.venv/${NC}"
    if ask_yn "Reinstall dependencies anyway?"; then
        INSTALL_DEPS=true
    else
        INSTALL_DEPS=false
    fi
else
    info "Creating virtual environment in ${BOLD}.venv/${NC} ..."
    python3 -m venv .venv
    success "Virtual environment created."
    INSTALL_DEPS=true
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate

if $INSTALL_DEPS; then
    info "Installing Python dependencies from ${BOLD}requirements.txt${NC} ..."
    pip install -q -r requirements.txt
    success "Dependencies installed."
fi

# ─── Step 2: Browser engine ──────────────────────────────────────────

header "Step 2 / 6 — Browser engine (Playwright Chromium)"

if command -v uvx &>/dev/null; then
    info "Installing browser via ${BOLD}uvx browser-use install${NC} ..."
    uvx browser-use install
elif command -v playwright &>/dev/null; then
    info "Installing browser via ${BOLD}playwright install chromium${NC} ..."
    playwright install chromium
else
    info "Installing ${BOLD}uv${NC} first, then browser ..."
    pip install -q uv
    uvx browser-use install
fi
success "Browser engine ready."

# ─── Step 3: .env — API key & LLM config ─────────────────────────────

header "Step 3 / 6 — LLM provider & API key"

ENV_FILE="$PROJECT_DIR/.env"
WRITE_ENV=true

if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists."
    if ! ask_yn "Overwrite it with fresh values?" "n"; then
        WRITE_ENV=false
        success "Keeping existing .env"
    fi
fi

if $WRITE_ENV; then
    dim "The agent needs an LLM to operate. Pick your provider."
    dim "Your API key will be stored in: ${BOLD}.env${NC}"
    echo ""

    provider=$(ask_choice "Which LLM provider will you use?" \
        "openai" \
        "anthropic" \
        "google" \
        "ollama (local, no API key needed)")

    # Normalize
    case "$provider" in
        openai)     LLM_PROVIDER="openai"    ;;
        anthropic)  LLM_PROVIDER="anthropic" ;;
        google)     LLM_PROVIDER="google"    ;;
        *)          LLM_PROVIDER="ollama"    ;;
    esac

    # Model
    case "$LLM_PROVIDER" in
        openai)     default_model="gpt-4.1-mini" ;;
        anthropic)  default_model="claude-sonnet-4-5-20250929" ;;
        google)     default_model="gemini-2.5-flash" ;;
        ollama)     default_model="llama3.1:70b" ;;
    esac

    echo ""
    dim "Model name — the LLM model the agent will call."
    LLM_MODEL=$(ask_input "Model name" "$default_model")

    # API key
    API_KEY_LINE=""
    if [[ "$LLM_PROVIDER" != "ollama" ]]; then
        echo ""
        case "$LLM_PROVIDER" in
            openai)     key_name="OPENAI_API_KEY"    ;;
            anthropic)  key_name="ANTHROPIC_API_KEY"  ;;
            google)     key_name="GOOGLE_API_KEY"     ;;
        esac
        dim "Your ${key_name} is required to authenticate with the LLM API."
        dim "It will be stored in ${BOLD}.env${NC} and is git-ignored."
        API_KEY=$(ask_input "${key_name}")
        API_KEY_LINE="${key_name}=${API_KEY}"
    fi

    # Google Vertex AI
    USE_VERTEX_AI=""
    GCP_PROJECT=""
    GCP_LOCATION=""
    if [[ "$LLM_PROVIDER" == "google" ]]; then
        echo ""
        dim "Google supports two authentication modes:"
        dim "  1) Gemini API — uses a GOOGLE_API_KEY (simpler)"
        dim "  2) Vertex AI  — uses gcloud ADC + a GCP project (no API key)"
        if ask_yn "Use Vertex AI instead of a Gemini API key?" "n"; then
            USE_VERTEX_AI="true"
            GCP_PROJECT=$(ask_input "GCP project ID")
            GCP_LOCATION=$(ask_input "GCP location" "us-central1")
            # Clear the API key line since Vertex uses ADC
            API_KEY_LINE=""
        fi
    fi

    # Chrome profile
    echo ""
    dim "Chrome profile path — lets the agent reuse your logged-in browser"
    dim "session (LinkedIn, etc.) so it skips login walls and CAPTCHAs."
    dim "Find yours: open Chrome → navigate to chrome://version → \"Profile Path\"."
    dim "Use the ${BOLD}parent directory${NC} of that path."
    CHROME_PATH=$(ask_input "Chrome profile path (leave blank to skip)" "")

    # Write .env
    {
        echo "# ── LLM Provider ─────────────────────────────────────────────"
        echo "LLM_PROVIDER=${LLM_PROVIDER}"
        echo "LLM_MODEL=${LLM_MODEL}"
        echo ""
        if [[ -n "$API_KEY_LINE" ]]; then
            echo "# ── API Key ────────────────────────────────────────────────"
            echo "$API_KEY_LINE"
            echo ""
        fi
        if [[ "$LLM_PROVIDER" == "ollama" ]]; then
            echo "# ── Ollama ─────────────────────────────────────────────────"
            echo "OLLAMA_BASE_URL=http://localhost:11434"
            echo ""
        fi
        if [[ -n "$USE_VERTEX_AI" ]]; then
            echo "# ── Google Vertex AI ─────────────────────────────────────"
            echo "USE_VERTEX_AI=true"
            echo "GCP_PROJECT=${GCP_PROJECT}"
            echo "GCP_LOCATION=${GCP_LOCATION}"
            echo ""
        fi
        if [[ -n "$CHROME_PATH" ]]; then
            echo "# ── Browser ────────────────────────────────────────────────"
            echo "CHROME_PROFILE_PATH=${CHROME_PATH}"
        fi
    } > "$ENV_FILE"

    success "Saved LLM config to ${BOLD}.env${NC}"
fi

# ─── Step 4: Config files ────────────────────────────────────────────

header "Step 4 / 6 — Config files"

copy_config() {
    local src="$1" dest="$2" label="$3"
    if [[ -f "$dest" ]]; then
        if ask_yn "  ${BOLD}${label}${NC} already exists. Overwrite with template?" "n"; then
            cp "$src" "$dest"
            success "Replaced ${BOLD}${label}${NC}"
        else
            success "Kept existing ${BOLD}${label}${NC}"
        fi
    else
        cp "$src" "$dest"
        success "Created ${BOLD}${label}${NC}"
    fi
}

dim "Config files hold your personal profile, job search targets, and agent"
dim "settings. Each is copied from its template and can be edited later."
echo ""

dim "  ${BOLD}config/profile.py${NC}    — your name, email, skills, work auth, filters"
dim "  ${BOLD}config/job_titles.py${NC} — which roles/locations to search for"
dim "  ${BOLD}config/settings.py${NC}   — agent behavior (headless, steps, cover letters)"
echo ""

copy_config config/profile.example.py    config/profile.py    "config/profile.py"
copy_config config/job_titles.example.py config/job_titles.py "config/job_titles.py"
copy_config config/settings.example.py   config/settings.py   "config/settings.py"

# ─── Step 5: Resume ──────────────────────────────────────────────────

header "Step 5 / 6 — Resume"

dim "The agent reads your resume to answer screening questions and generate"
dim "cover letters. Place a PDF at: ${BOLD}resume/resume.pdf${NC}"
dim "Plain text will be extracted automatically on first run."
echo ""

if [[ -f "resume/resume.pdf" ]]; then
    success "Resume found at ${BOLD}resume/resume.pdf${NC}"
    if ask_yn "Replace it with a different file?" "n"; then
        RESUME_SRC=$(ask_input "Path to your resume PDF")
        if [[ -f "$RESUME_SRC" ]]; then
            cp "$RESUME_SRC" resume/resume.pdf
            # Remove stale extracted text so it regenerates
            rm -f resume/resume.txt
            success "Resume copied to ${BOLD}resume/resume.pdf${NC}"
        else
            error "File not found: ${RESUME_SRC}"
            warn "You can copy it manually later: cp /path/to/resume.pdf resume/resume.pdf"
        fi
    fi
else
    RESUME_SRC=$(ask_input "Path to your resume PDF (leave blank to skip)")
    if [[ -n "$RESUME_SRC" && -f "$RESUME_SRC" ]]; then
        cp "$RESUME_SRC" resume/resume.pdf
        success "Resume copied to ${BOLD}resume/resume.pdf${NC}"
    elif [[ -n "$RESUME_SRC" ]]; then
        error "File not found: ${RESUME_SRC}"
        warn "You can copy it manually later: cp /path/to/resume.pdf resume/resume.pdf"
    else
        warn "Skipped — remember to add your resume before running the agent."
    fi
fi

# ─── Step 6: Summary ─────────────────────────────────────────────────

header "Step 6 / 6 — All done!"

echo -e "${GREEN}${BOLD}Setup complete.${NC} Here's what to do next:\n"

echo -e "  ${BOLD}1.${NC} Edit your profile         ${DIM}→ config/profile.py${NC}"
echo -e "  ${BOLD}2.${NC} Edit your job searches     ${DIM}→ config/job_titles.py${NC}"
echo -e "  ${BOLD}3.${NC} (Optional) Tweak settings  ${DIM}→ config/settings.py${NC}"

if [[ ! -f "resume/resume.pdf" ]]; then
    echo -e "  ${BOLD}4.${NC} ${YELLOW}Add your resume${NC}           ${DIM}→ resume/resume.pdf${NC}"
fi

echo ""
echo -e "  Then run:"
echo -e "  ${BOLD}${CYAN}python main.py --dry-run${NC}        ${DIM}# preview prompts${NC}"
echo -e "  ${BOLD}${CYAN}python main.py --review${NC}         ${DIM}# run with approval before each submit${NC}"
echo -e "  ${BOLD}${CYAN}python main.py${NC}                  ${DIM}# full auto${NC}"
echo ""
