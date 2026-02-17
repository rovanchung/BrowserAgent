#!/usr/bin/env python3
"""
BrowserAgent — Autonomous browser agent for job applications.

Usage:
    python main.py                    # Run with default config
    python main.py --provider openai  # Override LLM provider
    python main.py --model gpt-4.1   # Override model name
    python main.py --headless         # Run in headless mode
    python main.py --url <link>       # Apply to a specific job posting
    python main.py --dry-run          # Print the task prompt without running
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything reads os.getenv
load_dotenv()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BrowserAgent — Autonomous job application agent",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google", "ollama"],
        help="LLM provider (overrides config/settings.py and .env)",
    )
    parser.add_argument(
        "--model",
        help="Model name (overrides config/settings.py and .env)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser without a visible window",
    )
    parser.add_argument(
        "--url",
        help="Apply directly to a single job posting URL (skips search)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the task prompt and exit without running the browser",
    )
    parser.add_argument(
        "--initial-actions",
        action="store_true",
        help="Use browser-use initial_actions to navigate directly to search "
        "results (skips LLM navigation steps, saves tokens)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Pause for human approval before submitting each application",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Keep the browser open after the agent finishes",
    )
    return parser.parse_args()


def _apply_overrides(args: argparse.Namespace) -> None:
    """Patch config.settings with CLI overrides before anything else imports them."""
    import config.settings as settings

    if args.provider:
        settings.LLM_PROVIDER = args.provider
    if args.model:
        settings.LLM_MODEL = args.model
    if args.headless:
        settings.HEADLESS = True


def _check_prerequisites() -> None:
    """Verify that required files exist and generate resume.txt from PDF."""
    from config.settings import RESUME_PATH, RESUME_PDF_PATH
    from src.utils.pdf_to_text import pdf_to_text

    if not RESUME_PDF_PATH.exists():
        print(f"ERROR: Resume PDF not found at {RESUME_PDF_PATH}")
        print("Place your resume.pdf in the resume/ folder, then re-run.")
        sys.exit(1)

    # Auto-generate the plain-text resume from the PDF
    print(f"  Generating {RESUME_PATH.name} from {RESUME_PDF_PATH.name}...")
    pdf_to_text(RESUME_PDF_PATH, RESUME_PATH)


def _print_banner() -> None:
    from config.settings import LLM_MODEL, LLM_PROVIDER

    print(r"""
 ____                                       _                    _
| __ ) _ __ _____      _____  ___ _ __     / \   __ _  ___ _ __ | |_
|  _ \| '__/ _ \ \ /\ / / __|/ _ \ '__|   / _ \ / _` |/ _ \ '_ \| __|
| |_) | | | (_) \ V  V /\__ \  __/ |     / ___ \ (_| |  __/ | | | |_
|____/|_|  \___/ \_/\_/ |___/\___|_|    /_/   \_\__, |\___|_| |_|\__|
                                                |___/
    """)
    print(f"  LLM:  {LLM_PROVIDER} / {LLM_MODEL}")
    print(
        f"  Mode: {'headless' if __import__('config.settings', fromlist=['HEADLESS']).HEADLESS else 'visible browser'}"
    )
    print()


def _check_configs() -> None:
    """Ensure config files have been copied from their .example templates."""
    config_dir = Path(__file__).resolve().parent / "config"
    required = ["profile.py", "job_titles.py", "settings.py"]
    missing = [f for f in required if not (config_dir / f).exists()]
    if missing:
        print("ERROR: Missing config files:")
        for f in missing:
            print(
                f"  - config/{f}  (copy from config/{f.replace('.py', '.example.py')})"
            )
        print("\nSee README.md for setup instructions.")
        sys.exit(1)


async def main() -> None:
    args = parse_args()
    _check_configs()
    _apply_overrides(args)

    # Now import everything that depends on settings
    from config import job_titles
    from config.settings import RESUME_PATH
    from src.agent.job_agent import (
        run_job_search,
        run_single_apply,
        _build_task_prompt,
        _build_apply_prompt,
    )
    from src.agent.llm import build_llm

    _check_prerequisites()

    if args.dry_run:
        print("=== DRY RUN — Task prompts ===\n")
        if args.url:
            print(f"--- Direct apply: {args.url} ---")
            print(_build_apply_prompt(args.url))
        else:
            for search in job_titles.SEARCHES:
                print(f"--- Search: {search['title']} in {search['location']} ---")
                print(_build_task_prompt(search))
                print()
        return

    _print_banner()

    llm = build_llm()

    if args.url:
        summary = await run_single_apply(
            llm, args.url, keep_alive=args.keep_alive, review_before_submit=args.review
        )
    else:
        summary = await run_job_search(
            llm,
            keep_alive=args.keep_alive,
            use_initial_actions=args.initial_actions,
            review_before_submit=args.review,
        )

    print("\n" + "=" * 60)
    print("  Run Complete")
    print("=" * 60)
    print(f"  Reviewed: {summary.total_reviewed}")
    print(f"  Applied:  {summary.total_applied}")
    print(f"  Skipped:  {summary.total_skipped}")
    print(f"  Failed:   {summary.total_failed}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
