"""
Pause/resume gate for the browser agent.

Press Ctrl+Z to toggle pause.  The agent will pause before its next
action and resume when Ctrl+Z is pressed again.
"""

from __future__ import annotations

import threading

_pause_event = threading.Event()
_pause_event.set()  # starts unpaused
_paused = False


def toggle_pause(*_) -> None:
    """Toggle the pause state.  Intended as a signal handler for SIGTSTP."""
    global _paused
    _paused = not _paused
    if _paused:
        _pause_event.clear()
        print(f"\n{'='*60}", flush=True)
        print("  PAUSED  —  Press Ctrl+Z again to resume", flush=True)
        print(f"{'='*60}\n", flush=True)
    else:
        _pause_event.set()
        print(f"\n{'='*60}", flush=True)
        print("  RESUMED", flush=True)
        print(f"{'='*60}\n", flush=True)


def wait_if_paused() -> None:
    """Block the caller until the agent is unpaused."""
    _pause_event.wait()


def is_paused() -> bool:
    return _paused
