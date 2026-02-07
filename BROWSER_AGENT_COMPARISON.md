# Autonomous Browser Agent Solutions for Job Application Automation

> **Goal**: An AI agent that can autonomously search for jobs, generate cover letters, and apply to qualified positions — given your resume and preferences in advance.

---

## TL;DR Recommendation

| If you want...                          | Use                        |
|-----------------------------------------|----------------------------|
| Easiest setup + largest community       | **Browser Use**            |
| Most robust production workflows        | **Skyvern**                |
| Most reliable on complex JS job portals | **Playwright MCP + Claude**|

---

## The Three Best Solutions

### 1. Browser Use
### 2. Skyvern
### 3. Playwright MCP (+ LLM orchestration)

---

## Solution 1: Browser Use

> *"Read my CV & find ML jobs on LinkedIn, save them to a file, and then start applying for them in new tabs"* — from their README

| Attribute           | Details                                                   |
|---------------------|-----------------------------------------------------------|
| **Repository**      | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| **Stars**           | ~78,000                                                   |
| **License**         | MIT (fully permissive)                                    |
| **Language**        | Python                                                    |
| **Browser Engine**  | Chrome DevTools Protocol (CDP) — migrated from Playwright |
| **AI Approach**     | Hybrid DOM extraction + Vision (screenshots)              |
| **Setup Complexity**| Low — `pip install browser-use`                           |

### How It Works

```
User gives natural language task
    → Agent observes browser (DOM tree + screenshot)
        → LLM decides next action(s)
            → Execute via CDP (click, type, scroll, navigate)
                → Repeat until task complete (max 100 steps)
```

Browser Use takes a **hybrid approach**: it extracts an optimized DOM representation AND takes screenshots, sending both to the LLM. This lets the AI reason both structurally (HTML elements) and visually (like a human would). The agent loop is event-driven with watchdog services for downloads and crash recovery.

### LLM Support

| Provider          | How to Use                              | Recommended Models              |
|-------------------|-----------------------------------------|---------------------------------|
| **OpenAI**        | `ChatOpenAI(model="gpt-4.1-mini")`     | gpt-4.1 (best), gpt-4.1-mini   |
| **Anthropic**     | `ChatAnthropic(model="claude-sonnet-4-0")` | claude-sonnet-4-0            |
| **Google**        | `ChatGoogleGenerativeAI()`             | gemini-2.5-flash (best balance) |
| **Ollama (local)**| `ChatOllama(model="llama3.1:8b")`      | llama3.1, qwen2.5, deepseek-r1 |
| **LM Studio**     | `ChatOpenAI(base_url="http://localhost:1234/v1")` | Any OpenAI-compatible model |
| **Groq**          | Via LangChain                           | llama4 (fastest)                |
| **Azure/Bedrock** | Via LangChain                           | Any hosted model                |

**Local model caveat**: Smaller models (7B-13B) struggle with complex multi-step reasoning and often produce malformed JSON. Best results with 70B+ models or commercial APIs.

### Setup for Job Automation

```bash
# Install
pip install browser-use
uvx browser-use install   # installs Chromium

# Set API key (pick one)
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Example: Job Application Agent

```python
import asyncio
from browser_use import Agent, Browser, Tools
from langchain_openai import ChatOpenAI

tools = Tools()

@tools.action(description="Save job listing details to a file")
def save_job(title: str, company: str, url: str, filename: str = "jobs.csv") -> str:
    with open(filename, "a") as f:
        f.write(f"{title},{company},{url}\n")
    return f"Saved {title} at {company}"

@tools.action(description="Read resume content from file")
def read_resume(filepath: str = "resume.txt") -> str:
    with open(filepath, "r") as f:
        return f.read()

async def main():
    browser = Browser()
    llm = ChatOpenAI(model="gpt-4.1-mini")

    agent = Agent(
        task="""
        1. Read my resume from resume.txt
        2. Go to LinkedIn jobs and search for 'Senior Software Engineer' in 'San Francisco'
        3. For each of the first 5 results:
           - Check if I'm qualified based on my resume
           - If qualified, save the job details and open the application in a new tab
           - Fill out the application form using my resume data
        4. If you need clarification, ask me
        """,
        llm=llm,
        browser=browser,
        tools=tools,
    )
    history = await agent.run()
    print(history.final_result())

asyncio.run(main())
```

### Strengths

- Largest community (78k stars) — most tutorials, examples, community support
- MIT license — no restrictions on use
- Job application is a **first-class demo use case** in their docs
- Custom tools/actions let you extend functionality (save to DB, send notifications, etc.)
- Multi-tab support — can open applications in parallel tabs
- Can reuse real browser profiles with saved logins/cookies
- CLI tool for interactive debugging (`browser-use open`, `browser-use click`, etc.)
- Structured Pydantic output for data extraction
- Active daily development (latest release: Feb 6, 2026)
- Y Combinator backed

### Limitations

- **CAPTCHAs**: Major blocker. Open-source version cannot solve CAPTCHAs. Need third-party solvers (CapSolver) or their paid Cloud service
- **Anti-bot detection**: Automated browsing can trigger bot detection on job sites
- **Chromium only**: No Firefox/WebKit (due to CDP migration)
- **Non-deterministic**: Same task may take different paths or fail on repeated runs
- **Cost**: Each step = 1 LLM call with large DOM context. A 20-step job application ~$0.50-2.00 with GPT-4
- **Login/2FA**: QR codes and phone verification are barriers

---

## Solution 2: Skyvern

> Vision-first browser automation — sees the page like a human, no selectors needed

| Attribute           | Details                                                   |
|---------------------|-----------------------------------------------------------|
| **Repository**      | [Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern) |
| **Stars**           | ~20,300                                                   |
| **License**         | AGPL-3.0 (copyleft — derivatives must be open-source)     |
| **Language**        | Python + TypeScript SDK                                   |
| **Browser Engine**  | Playwright (Chromium)                                     |
| **AI Approach**     | Screenshot → Vision LLM (no DOM parsing)                  |
| **Setup Complexity**| Medium — `pip install skyvern` + PostgreSQL               |

### How It Works

```
Screenshot of current viewport
    → Vision LLM identifies elements visually
        → Planner Agent breaks goal into sub-steps
            → Actor Agent executes browser actions
                → Validator Agent checks results
                    → Self-correcting loop until done
```

Skyvern's key innovation is **pure vision-based reasoning**. Instead of parsing HTML/DOM, it screenshots the page and asks a Vision LLM (GPT-4o, Claude) to identify buttons, forms, and links by their visual appearance. This makes it resilient to layout changes and works on sites never seen before.

**Explore → Replay Pattern** (unique to Skyvern):
1. First run: Full LLM pipeline explores the site (expensive, ~280s)
2. Successful path compiled into a **deterministic Playwright script**
3. Subsequent runs: No LLM needed — fast (~120s) and cheap ($0.04 vs $0.11)
4. If site changes: LLM wakes up, heals the path, recompiles

This is ideal for job applications where you apply to many positions on the same portal.

### LLM Support

| Provider          | How to Configure                                    |
|-------------------|-----------------------------------------------------|
| **OpenAI**        | `LLM_KEY=openai:gpt-4o`                            |
| **Anthropic**     | `LLM_KEY=anthropic:claude-sonnet-4-0`              |
| **Google Gemini** | `LLM_KEY=gemini:gemini-2.5-pro`                    |
| **Azure OpenAI**  | Via environment variables                           |
| **AWS Bedrock**   | Via environment variables                           |
| **OpenRouter**    | Access to many models                               |
| **Ollama (local)**| `ENABLE_OLLAMA=true`, `OLLAMA_MODEL=qwen2.5:7b-instruct` |
| **Any OpenAI-compatible** | `ENABLE_OPENAI_COMPATIBLE=true`, set base URL |

### Setup for Job Automation

```bash
# Option A: pip (simplest)
pip install skyvern
skyvern quickstart       # Sets up config + PostgreSQL
skyvern run all          # Starts backend + UI on port 8080

# Option B: Docker
skyvern init llm         # Generates .env with LLM config
# Edit .env to add your API key
docker compose up -d     # Starts everything including PostgreSQL
```

**Requirements**: Python 3.11-3.12, Node.js, PostgreSQL (auto-provisioned by quickstart)

### Example: Job Application Workflow

Skyvern has a visual **Workflow Builder** (at `localhost:8080`) and API/SDK access:

```python
from skyvern import Skyvern
import asyncio

async def main():
    skyvern = Skyvern(base_url="http://localhost:8080")

    # Simple task-based approach
    task = await skyvern.create_task(
        url="https://company.com/careers/senior-engineer",
        prompt="""
        Apply for this job position. Use the following information:
        - Name: Jane Doe
        - Email: jane.doe@email.com
        - Phone: 555-0123
        - Years of experience: 8
        - Current title: Senior Software Engineer
        Upload the resume from the provided file.
        Answer screening questions based on my background in Python, AWS, and distributed systems.
        """,
        file_url="https://your-storage.com/resume.pdf",
    )

    # Monitor task progress
    result = await skyvern.get_task(task.task_id)
    print(result.status, result.extracted_information)

asyncio.run(main())
```

**Workflow approach** (for batch applications):
```yaml
# Conceptual workflow (configured via UI or API)
blocks:
  - type: file_parsing
    file: resume.pdf        # Parse resume for structured data

  - type: for_loop
    items: job_urls          # List of job application URLs
    body:
      - type: browser_task
        prompt: "Apply for this job using the parsed resume data"
        data_extraction:
          applied: boolean
          confirmation_id: string

      - type: send_email
        to: "jane@email.com"
        subject: "Application submitted: {{job_title}}"
```

### Strengths

- **Vision-first approach** — works on any website without site-specific configuration
- **Self-correcting** — Validator Agent catches failures and retries with alternative strategies
- **Explore → Replay** — massive cost/speed savings for repeated workflows (2.3x faster, 2.7x cheaper)
- **Production-ready infrastructure** — Web UI, REST API, Python & TypeScript SDKs, webhook notifications
- **Workflow system** — first-class support for chaining steps, loops, conditionals, file parsing
- **TOTP/2FA support** — handles common authentication methods
- **Password manager integration** — Bitwarden support built in
- **Best-in-class form filling** — SOTA on WebBench WRITE tasks benchmark
- **MCP server** — integrates with Claude Desktop and other MCP clients
- **Integration ecosystem** — Zapier, Make.com, N8N connectors
- **Livestreaming** — watch the agent work in real-time
- Y Combinator backed, $2.7M seed raised Dec 2025

### Limitations

- **AGPL-3.0 license** — if you modify and serve it, you must open-source your changes
- **CAPTCHA solving not in open-source** — only available in Skyvern Cloud
- **~64% benchmark accuracy** — roughly 1 in 3 complex tasks may fail on first try
- **Heavier setup** — requires PostgreSQL, more infrastructure than Browser Use
- **No native multi-tab AI reasoning** — agent reasons about single viewport
- **Local models significantly weaker** — Ollama vision models lag far behind GPT-4o/Claude
- **Python 3.13 not supported**
- **Ollama + Docker integration can be finicky** (known GitHub issue #2963)
- **Telemetry enabled by default** — opt out with `SKYVERN_TELEMETRY=false`

---

## Solution 3: Playwright MCP + LLM

> The most reliable browser control — powered by accessibility trees, not pixels or HTML

| Attribute           | Details                                                   |
|---------------------|-----------------------------------------------------------|
| **Repository**      | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) |
| **Stars**           | ~25,000+                                                  |
| **License**         | Apache-2.0 (fully permissive)                             |
| **Language**        | TypeScript (npm package)                                  |
| **Browser Engine**  | Playwright (Chromium, Firefox, WebKit)                    |
| **AI Approach**     | Accessibility tree snapshots → LLM reasoning              |
| **Setup Complexity**| Low-Medium — requires MCP client (Claude Desktop/Code)    |

### How It Works

```
LLM receives user task
    → Calls Playwright MCP tools (browser_navigate, browser_click, etc.)
        → Playwright MCP returns accessibility tree snapshot
            → LLM reasons about page structure
                → Calls next tool
                    → Repeat until task complete
```

Playwright MCP is **not a standalone agent** — it's a **tool server** that gives any MCP-compatible LLM the ability to control a browser. The LLM (Claude, GPT-4, etc.) does all the reasoning; Playwright MCP handles the execution.

The key innovation is using **accessibility tree snapshots** instead of screenshots or raw HTML. The accessibility tree is:
- **Deterministic** — same page always produces the same tree
- **Compact** — much smaller than full HTML, fits easily in LLM context
- **Semantic** — describes what elements *are* (button, textbox, link) not how they look
- **JavaScript-aware** — captures dynamic content that static HTML misses

### LLM Support

Playwright MCP is **model-agnostic** — it works with whatever LLM your MCP client uses:

| MCP Client              | LLM Options                                      |
|-------------------------|--------------------------------------------------|
| **Claude Desktop**      | Claude 4 Opus, Claude 4 Sonnet, Claude 3.5 Sonnet|
| **Claude Code (CLI)**   | Claude 4 Opus, Claude 4 Sonnet                   |
| **Cursor IDE**          | Claude, GPT-4, Gemini (configurable)              |
| **VS Code + Copilot**   | GPT-4, Claude (via extensions)                    |
| **Custom MCP client**   | Any LLM — OpenAI, Anthropic, Ollama, LM Studio   |

For local models, you would build a simple MCP client that connects to Ollama and calls Playwright MCP tools. This requires more custom code but gives you full control.

### Setup for Job Automation

**Option A: With Claude Desktop (simplest)**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Then in Claude Desktop, simply type your task:
> "Go to indeed.com, search for 'Software Engineer' in 'Austin TX', open the first 5 results, and for each one that requires Python experience, fill out the Easy Apply form with: Name: John Doe, Email: john@email.com, Phone: 555-0123. Upload my resume from ~/Documents/resume.pdf."

**Option B: With Claude Code (CLI)**

```bash
# Install Playwright MCP
npm install -g @playwright/mcp

# Add to Claude Code MCP config
claude mcp add playwright -- npx @playwright/mcp@latest
```

Then use Claude Code with browser automation capabilities built in.

**Option C: Custom Python Script (most flexible)**

```python
"""
Custom MCP client that connects an LLM to Playwright MCP
for autonomous job application.
"""
import asyncio
import json
from openai import OpenAI  # or anthropic, ollama, etc.

# This is a simplified conceptual example.
# In practice, use an MCP client library like `mcp` (pip install mcp)

client = OpenAI()  # or Anthropic(), or Ollama()

SYSTEM_PROMPT = """
You are a job application assistant. You have access to browser tools via Playwright MCP.
You will be given a resume and job search criteria. Your task is to:
1. Navigate to job boards
2. Search for matching positions
3. Evaluate each position against the resume
4. For qualified positions, fill out and submit the application
5. Generate a tailored cover letter for each application

Available tools: browser_navigate, browser_click, browser_type,
browser_snapshot, browser_tab_list, browser_file_upload, etc.

Resume:
{resume_content}

Job criteria:
- Role: {target_role}
- Location: {location}
- Min salary: {min_salary}
- Must-have skills: {required_skills}
"""

async def run_job_agent():
    with open("resume.txt") as f:
        resume = f.read()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(
            resume_content=resume,
            target_role="Senior Software Engineer",
            location="Remote",
            min_salary="$150,000",
            required_skills="Python, AWS, Kubernetes"
        )},
        {"role": "user", "content": "Start searching on LinkedIn and Indeed. Apply to all qualified positions."}
    ]

    # Agent loop: LLM reasons → calls MCP tools → observes results → repeats
    while True:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            tools=playwright_mcp_tools,  # MCP tools registered as OpenAI function calls
        )
        # Process tool calls, execute via MCP, feed results back...
        # (Full implementation requires MCP client library)

asyncio.run(run_job_agent())
```

### Strengths

- **Most reliable on complex JavaScript-heavy sites** — accessibility tree captures dynamic content that DOM parsing and screenshots miss (Workday, Greenhouse, Lever, Taleo)
- **Deterministic page representation** — no vision model ambiguity
- **Multi-browser support** — Chromium, Firefox, AND WebKit
- **File upload support** — native Playwright file chooser API
- **Microsoft-backed** — maintained by the Playwright team, weekly releases, ~980K npm downloads
- **Apache-2.0 license** — fully permissive
- **Most actively maintained** — v0.0.62 released Jan 31, 2026
- **No vision model cost** — accessibility tree is free to generate, only LLM reasoning costs
- **Composable** — can combine with any LLM, any MCP client, any workflow orchestration
- **Token-efficient** — new CLI mode optimized for coding agents
- **Cover letter generation is natural** — the LLM already has your resume context and the job description, so generating a tailored cover letter is just another prompt

### Limitations

- **Not a standalone agent** — requires an MCP client + LLM to orchestrate. More assembly required
- **No built-in workflow system** — you build the orchestration yourself (or use Claude Desktop/Code)
- **No CAPTCHA handling** — same limitation as all tools
- **No explore-then-replay optimization** — every run uses the LLM (no compiled fast paths)
- **Accessibility tree can be incomplete** — some sites have poor accessibility markup
- **Requires MCP ecosystem knowledge** — newer paradigm, fewer tutorials than direct Python SDKs
- **No built-in Web UI** — purely tool-based, no visual dashboard

---

## Deep Comparison

### Architecture Comparison

```
Browser Use:       Task → [DOM + Screenshot] → LLM → CDP Actions → Loop
Skyvern:           Task → [Screenshot only]  → Vision LLM → Playwright Actions → Validator → Loop
Playwright MCP:    Task → LLM → [MCP Tool Call] → Accessibility Tree → LLM → Loop
```

| Aspect                    | Browser Use              | Skyvern                    | Playwright MCP            |
|---------------------------|--------------------------|----------------------------|---------------------------|
| **Page understanding**    | DOM tree + screenshots   | Screenshots only (vision)  | Accessibility tree        |
| **Element identification**| XPath from DOM           | Visual coordinates         | Accessibility refs        |
| **Resilience to layout changes** | Medium            | High (vision-based)        | High (semantic-based)     |
| **Works on unseen sites** | Yes                      | Yes                        | Yes                       |
| **Deterministic output**  | No                       | Yes (replay mode)          | Yes (accessibility tree)  |
| **Token efficiency**      | Medium (large DOM)       | Low (screenshots are big)  | High (compact tree)       |

### Cost Comparison (Estimated per Job Application)

Assuming a 15-step application form with GPT-4.1-mini:

| Cost Factor               | Browser Use              | Skyvern                    | Playwright MCP            |
|---------------------------|--------------------------|----------------------------|---------------------------|
| **LLM cost per step**     | ~$0.03 (DOM + screenshot)| ~$0.05 (screenshot heavy)  | ~$0.01 (compact tree)     |
| **First application**     | ~$0.45                   | ~$0.75                     | ~$0.15                    |
| **Repeated (same site)**  | ~$0.45 (no optimization) | ~$0.04 (replay mode!)      | ~$0.15                    |
| **100 applications (mixed sites)** | ~$45           | ~$30 (with replay savings) | ~$15                      |
| **With local model (Ollama)** | Free (but lower accuracy) | Free (but much lower accuracy) | Free (with custom MCP client) |

### Feature Matrix for Job Application Automation

| Feature                          | Browser Use | Skyvern | Playwright MCP |
|----------------------------------|:-----------:|:-------:|:--------------:|
| Search jobs on LinkedIn/Indeed   | Yes         | Yes     | Yes            |
| Fill multi-page application forms| Yes         | Yes     | Yes            |
| Upload resume (PDF)              | Basic       | Yes     | Yes            |
| Generate tailored cover letter   | Via LLM     | Via LLM | Via LLM        |
| Handle screening questions       | Yes         | Yes     | Yes            |
| Multi-tab parallel applications  | Yes         | No      | Yes            |
| Reuse saved browser login        | Yes         | Yes     | Yes            |
| Self-correction on errors        | Basic retry | Yes (Validator Agent) | Via LLM retry |
| Batch workflow (loop over URLs)  | Custom code | Built-in workflow | Custom code  |
| Real-time monitoring             | CLI tools   | Livestream UI | Via MCP client |
| Works on Workday/Greenhouse      | Often       | Often   | Best           |
| CAPTCHA handling                 | No*         | No*     | No*            |
| 2FA / TOTP support               | No          | Yes     | No             |
| Password manager integration     | No          | Yes (Bitwarden) | No        |
| Result export (CSV/JSON)         | Custom tools| Built-in extraction | Custom code |
| Email notifications              | Custom tools| Built-in workflow block | Custom code |

> *\* No free tool solves CAPTCHAs natively. Workarounds: use a logged-in browser profile, third-party solvers (CapSolver ~$1/1000 solves), or apply on CAPTCHA-free portals.*

### LLM Compatibility

| LLM Provider        | Browser Use | Skyvern | Playwright MCP |
|----------------------|:-----------:|:-------:|:--------------:|
| OpenAI (GPT-4)      | Yes         | Yes     | Yes*           |
| Anthropic (Claude)   | Yes         | Yes     | Yes*           |
| Google (Gemini)      | Yes         | Yes     | Yes*           |
| Ollama (local)       | Yes         | Yes     | Yes**          |
| LM Studio (local)    | Yes         | Yes     | Yes**          |
| Groq                 | Yes         | Yes     | Yes*           |
| Azure OpenAI         | Yes         | Yes     | Yes*           |
| AWS Bedrock          | Yes         | Yes     | Yes*           |

> *\* Via MCP client configuration — the LLM choice is on the client side*
> *\*\* Requires building a custom MCP client that connects to local models*

### Setup & Maintenance

| Factor                   | Browser Use              | Skyvern                    | Playwright MCP            |
|--------------------------|--------------------------|----------------------------|---------------------------|
| **Install command**      | `pip install browser-use`| `pip install skyvern`      | `npx @playwright/mcp`    |
| **Dependencies**         | Python 3.11+, Chromium   | Python 3.11-3.12, Node.js, PostgreSQL | Node.js, MCP client |
| **Database required**    | No                       | Yes (PostgreSQL)           | No                        |
| **Web UI included**      | No (CLI only)            | Yes (port 8080)            | No                        |
| **Docker support**       | Community only           | Official docker-compose    | No                        |
| **Time to first run**    | ~5 minutes               | ~15 minutes                | ~5 minutes                |
| **Maintenance burden**   | Low                      | Medium (DB, services)      | Low                       |
| **GitHub activity**      | Very active (daily)      | Very active                | Very active (weekly)      |
| **Commercial backing**   | YC + Browser Use Inc.    | YC + $2.7M seed            | Microsoft                 |

---

## Recommended Setup for Your Use Case

### The Pragmatic Choice: Browser Use

For someone who wants to get started quickly with job application automation and has access to an API key:

```bash
# 1. Setup
mkdir job-agent && cd job-agent
python -m venv .venv && source .venv/bin/activate
pip install browser-use langchain-openai
uvx browser-use install

# 2. Create your resume file
cat > resume.txt << 'EOF'
[Paste your resume text here]
EOF

# 3. Create the agent script
cat > job_agent.py << 'PYEOF'
import asyncio
from browser_use import Agent, Browser, Tools
from langchain_openai import ChatOpenAI

tools = Tools()

@tools.action(description="Save applied job to tracking file")
def track_application(title: str, company: str, url: str, status: str) -> str:
    with open("applications.csv", "a") as f:
        f.write(f'"{title}","{company}","{url}","{status}"\n')
    return f"Tracked: {title} at {company}"

async def main():
    browser = Browser()
    llm = ChatOpenAI(model="gpt-4.1-mini")

    with open("resume.txt") as f:
        resume = f.read()

    agent = Agent(
        task=f"""
        You are a job application assistant. Here is my resume:

        {resume}

        Instructions:
        1. Go to LinkedIn Jobs (linkedin.com/jobs)
        2. Search for 'Software Engineer' in 'Remote'
        3. Filter by 'Past Week' and 'Easy Apply'
        4. For each of the first 10 results:
           a. Open the job listing
           b. Check if I'm qualified (match skills from my resume)
           c. If qualified, click Easy Apply and fill the form with my info
           d. Track each application using the track_application tool
        5. Skip jobs that require skills I don't have
        6. If you encounter a CAPTCHA or blocker, skip that job and move to the next
        """,
        llm=llm,
        browser=browser,
        tools=tools,
    )
    history = await agent.run()
    print("=== RESULTS ===")
    print(history.final_result())

asyncio.run(main())
PYEOF

# 4. Set your API key and run
export OPENAI_API_KEY="sk-..."
python job_agent.py
```

### The Budget Choice: Browser Use + Ollama (Free)

```bash
# 1. Install Ollama and pull a model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.1:70b    # Best free option (needs ~40GB RAM)
# or for lower RAM:
ollama pull qwen2.5:7b      # Decent, needs ~8GB RAM

# 2. Setup
pip install browser-use langchain-ollama
uvx browser-use install

# 3. Use Ollama in your script
# Replace the LLM line with:
# from langchain_ollama import ChatOllama
# llm = ChatOllama(model="llama3.1:70b")
```

> **Warning**: Local models have significantly lower success rates on complex forms. Expect ~40-60% of applications to need manual intervention vs ~80-90% with GPT-4.

### The Power User Choice: Skyvern Workflows

If you're applying to many jobs on the same few portals (e.g., 50 applications on Workday sites):

```bash
# 1. Setup
pip install skyvern
skyvern quickstart
skyvern run all

# 2. Open http://localhost:8080
# 3. Use the visual Workflow Builder to create:
#    - A "File Parse" block for your resume
#    - A "For Loop" block over your list of job URLs
#    - A "Browser Task" block with your application prompt
#    - An "Email" block to notify you of each application

# The first run on each portal is slow (LLM explores).
# Subsequent runs on the same portal are fast and cheap (replay mode).
```

---

## CAPTCHA Strategy (All Solutions)

Since no free tool solves CAPTCHAs, here are practical workarounds:

1. **Use a logged-in browser profile** — Pre-authenticate manually, then let the agent reuse your session. Most sites don't CAPTCHA authenticated users.
   ```python
   # Browser Use example
   browser = Browser(config=BrowserConfig(
       chrome_instance_path="/path/to/your/chrome/profile"
   ))
   ```

2. **Target Easy Apply / CAPTCHA-free portals** — LinkedIn Easy Apply, AngelList, many company career pages don't have CAPTCHAs for logged-in users.

3. **Third-party CAPTCHA solvers** — CapSolver, 2Captcha (~$1-3 per 1000 solves). Integrate via custom tools/actions.

4. **Human-in-the-loop** — Configure the agent to pause and alert you when it hits a CAPTCHA.
   ```python
   # Browser Use example
   @tools.action(description="Ask user for help with CAPTCHA")
   def request_human_help(message: str) -> str:
       print(f"\n🔔 AGENT NEEDS HELP: {message}")
       input("Press Enter after solving the CAPTCHA...")
       return "Human resolved the issue, continue with the task"
   ```

---

## Final Verdict

| Criterion                     | Winner              | Why                                          |
|-------------------------------|---------------------|----------------------------------------------|
| **Easiest to start**          | Browser Use         | `pip install` + 10 lines of Python           |
| **Best for repeated workflows**| Skyvern            | Explore→Replay compiles to fast scripts      |
| **Most reliable on complex sites**| Playwright MCP | Accessibility tree handles JS-heavy portals  |
| **Cheapest with commercial API**| Playwright MCP   | Smallest token footprint per step            |
| **Cheapest overall (free)**   | Browser Use + Ollama| Best local model support                     |
| **Best form filling accuracy**| Skyvern             | SOTA on WebBench WRITE benchmarks            |
| **Best community/support**    | Browser Use         | 78K stars, active Discord, daily releases    |
| **Best for cover letters**    | Any (LLM-dependent) | All three use LLMs that can generate text    |
| **Most permissive license**   | Browser Use / Playwright MCP | MIT / Apache-2.0              |
| **Best production infrastructure**| Skyvern        | Web UI, API, SDKs, webhooks, integrations    |

**My recommendation**: Start with **Browser Use** for its simplicity and community. If you find yourself applying to 50+ jobs on the same portals, migrate to **Skyvern** for its replay optimization. If you're already using Claude Desktop/Code, just add **Playwright MCP** — it's the simplest path with the highest reliability.

---

*Last updated: February 7, 2026*
