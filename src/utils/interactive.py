"""
Interactive menu for BrowserAgent.

Shown when `python main.py` is run with no arguments.
Builds an argparse.Namespace identical to what CLI flags would produce.
Uses arrow keys + Enter for navigation (no typing required).
"""

from __future__ import annotations

import argparse
import sys
import tty
import termios
from pathlib import Path


# ── Terminal helpers ───────────────────────────────────────────────────


def _read_key() -> str:
    """Read a single keypress, handling arrow key escape sequences."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
        if ch == "\x1b":  # Escape sequence
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            return "esc"
        if ch in ("\r", "\n"):
            return "enter"
        if ch == " ":
            return "space"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _hide_cursor() -> None:
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def _show_cursor() -> None:
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def _move_up(n: int) -> None:
    if n > 0:
        sys.stdout.write(f"\033[{n}A")


def _clear_to_end() -> None:
    sys.stdout.write("\033[J")


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"


def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


def _cyan(text: str) -> str:
    return f"\033[36m{text}\033[0m"


def _invert(text: str) -> str:
    return f"\033[7m{text}\033[0m"


# ── Select one ─────────────────────────────────────────────────────────


def _select_one(title: str, options: list[tuple[str, str]]) -> int:
    """Arrow-key single-select menu. Returns 0-based index."""
    cursor = 0
    # options + blank + hint
    redraw_lines = len(options) + 2

    print(f"\n  {_bold(title)}\n")

    def _render_options(first: bool = False):
        if not first:
            _move_up(redraw_lines)
            _clear_to_end()
        for i, (label, desc) in enumerate(options):
            padded = f"{label:.<24s}"
            if i == cursor:
                print(f"    {_cyan('>')} {_invert(padded)} {_dim(desc)}")
            else:
                print(f"      {padded} {_dim(desc)}")
        print(f"\n  {_dim('Up/Down: move  Enter: select')}")

    _hide_cursor()
    try:
        _render_options(first=True)
        while True:
            key = _read_key()
            if key == "up":
                cursor = (cursor - 1) % len(options)
                _render_options()
            elif key == "down":
                cursor = (cursor + 1) % len(options)
                _render_options()
            elif key == "enter":
                _move_up(redraw_lines)
                _clear_to_end()
                for i, (label, desc) in enumerate(options):
                    if i == cursor:
                        print(f"    {_green('>')} {label}  {_dim(desc)}")
                    else:
                        print(f"      {_dim(label)}")
                print()
                return cursor
    except (KeyboardInterrupt, EOFError):
        _show_cursor()
        print()
        sys.exit(130)
    finally:
        _show_cursor()


# ── Select many ────────────────────────────────────────────────────────


def _select_many(title: str, options: list[tuple[str, str, bool]]) -> list[bool]:
    """Arrow-key multi-select checklist. Space/Enter to toggle, Enter on Submit to confirm."""
    selected = [default for _, _, default in options]
    cursor = 0
    # options + submit button + blank + hint
    num_rows = len(options) + 1
    redraw_lines = num_rows + 2

    print(f"\n  {_bold(title)}\n")

    def _render_options(first: bool = False):
        if not first:
            _move_up(redraw_lines)
            _clear_to_end()
        for i, (label, desc, _) in enumerate(options):
            check = _green("[x]") if selected[i] else "[ ]"
            padded = f"{label:.<24s}"
            if i == cursor:
                print(f"    {_cyan('>')} {check} {_invert(padded)} {_dim(desc)}")
            else:
                print(f"      {check} {padded} {_dim(desc)}")
        # Submit row
        if cursor == len(options):
            print(f"    {_cyan('>')} {_invert(' Submit ')}")
        else:
            print(f"      {_dim('Submit')}")
        print(f"\n  {_dim('Up/Down: move  Space/Enter: toggle  Enter on Submit: confirm')}")

    _hide_cursor()
    try:
        _render_options(first=True)
        while True:
            key = _read_key()
            if key == "up":
                cursor = (cursor - 1) % num_rows
                _render_options()
            elif key == "down":
                cursor = (cursor + 1) % num_rows
                _render_options()
            elif key in ("space", "enter"):
                if cursor < len(options):
                    # Toggle the option
                    selected[cursor] = not selected[cursor]
                    _render_options()
                elif key == "enter":
                    # Submit (only Enter, not Space)
                    _move_up(redraw_lines)
                    _clear_to_end()
                    chosen = []
                    for i, (label, desc, _) in enumerate(options):
                        check = _green("[x]") if selected[i] else _dim("[ ]")
                        label_fmt = label if selected[i] else _dim(label)
                        print(f"      {check} {label_fmt}")
                        if selected[i]:
                            chosen.append(label)
                    if chosen:
                        print(f"\n  Selected: {', '.join(chosen)}")
                    else:
                        print(f"\n  Selected: {_dim('(none)')}")
                    return selected
    except (KeyboardInterrupt, EOFError):
        _show_cursor()
        print()
        sys.exit(130)
    finally:
        _show_cursor()


# ── Text prompt ────────────────────────────────────────────────────────


def _prompt(text: str, default: str = "") -> str:
    """Prompt for text input with an optional default."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"  {text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return value or default


# ── Progress detection ─────────────────────────────────────────────────


def _has_saved_progress() -> bool:
    output_dir = Path(__file__).resolve().parent.parent.parent / "output"
    return (output_dir / "progress.json").exists()


# ── Main menu ──────────────────────────────────────────────────────────


def interactive_menu() -> argparse.Namespace:
    """Run the interactive menu and return a Namespace matching CLI args."""
    from config.settings import LLM_MODEL, LLM_PROVIDER

    print()
    print(f"  {_bold('BrowserAgent')}")
    print(f"  {_dim('No flags detected — starting interactive setup')}")

    # ── Level 1: Run mode ──────────────────────────────────────────────

    mode = _select_one("What would you like to do?", [
        ("Search & Apply", "Run full job search pipeline"),
        ("Apply to URL", "Apply to a single job posting"),
        ("Dry Run", "Preview task prompts without running"),
    ])

    args = argparse.Namespace(
        provider=None,
        model=None,
        headless=False,
        url=None,
        dry_run=False,
        initial_actions=False,
        review=False,
        keep_alive=False,
        resume=False,
    )

    # ── Level 2: Mode-specific inputs ──────────────────────────────────

    if mode == 1:  # Apply to URL
        print()
        args.url = _prompt("Job posting URL")
        if not args.url:
            print("  URL is required for this mode.")
            sys.exit(1)

    if mode == 2:  # Dry Run
        args.dry_run = True
        print()
        url = _prompt("Job posting URL (optional, press Enter to preview all searches)")
        if url:
            args.url = url

    # ── Level 2: Options (multi-select) ────────────────────────────────

    if mode == 0:  # Search & Apply
        option_defs = []
        has_progress = _has_saved_progress()

        if has_progress:
            option_defs.append(
                ("Resume last run", "Continue from last interrupted position", True)
            )
        option_defs.extend([
            ("Fast navigation", "Navigate via URL params, skip LLM search steps (saves tokens)", False),
            ("Review mode", "Pause for your approval before each submit", False),
            ("Keep browser alive", "Keep tabs open after the run finishes", False),
            ("Headless", "Run without a visible browser window", False),
        ])

        toggles = _select_many("Options", option_defs)

        idx = 0
        if has_progress:
            args.resume = toggles[idx]; idx += 1
        args.initial_actions = toggles[idx]; idx += 1
        args.review = toggles[idx]; idx += 1
        args.keep_alive = toggles[idx]; idx += 1
        args.headless = toggles[idx]; idx += 1

        # Auto-enable initial-actions when resuming (needed for page offset)
        if args.resume and not args.initial_actions:
            print(f"\n  {_yellow('Note:')} --resume requires fast navigation to skip to the right page.")
            print(f"  Enabling fast navigation automatically.")
            args.initial_actions = True

    elif mode == 1:  # Apply to URL
        option_defs = [
            ("Review mode", "Pause for your approval before submit", False),
            ("Keep browser alive", "Keep tabs open after the run finishes", False),
            ("Headless", "Run without a visible browser window", False),
        ]
        toggles = _select_many("Options", option_defs)
        args.review = toggles[0]
        args.keep_alive = toggles[1]
        args.headless = toggles[2]

    # Dry Run has no runtime options

    # ── Level 3: LLM override ─────────────────────────────────────────

    if not args.dry_run:
        print(f"\n  {_bold('LLM Configuration')}")
        print(f"  Current: {_green(LLM_PROVIDER)} / {_green(LLM_MODEL)}")
        override = _prompt("Override provider? (openai/anthropic/google/ollama or Enter to keep)")
        if override:
            valid = {"openai", "anthropic", "google", "ollama"}
            if override.lower() not in valid:
                print(f"  Invalid provider. Choose from: {', '.join(sorted(valid))}")
                sys.exit(1)
            args.provider = override.lower()
            model = _prompt("Model name", LLM_MODEL)
            if model != LLM_MODEL:
                args.model = model

    # ── Summary ────────────────────────────────────────────────────────

    flags = _build_flag_summary(args)
    print(f"\n  {_bold('Starting:')} python main.py {flags}")
    if flags != "(default config)":
        print(f"  {_dim('Tip: next time you can run this directly to skip the menu')}")
    print()

    return args


def _build_flag_summary(args: argparse.Namespace) -> str:
    """Build a human-readable flag string from the namespace."""
    parts = []
    if args.dry_run:
        parts.append("--dry-run")
    if args.url:
        parts.append(f"--url {args.url}")
    if args.provider:
        parts.append(f"--provider {args.provider}")
    if args.model:
        parts.append(f"--model {args.model}")
    if args.resume:
        parts.append("--resume")
    if args.initial_actions:
        parts.append("--initial-actions")
    if args.review:
        parts.append("--review")
    if args.keep_alive:
        parts.append("--keep-alive")
    if args.headless:
        parts.append("--headless")
    return " ".join(parts) if parts else "(default config)"
