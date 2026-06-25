#!/usr/bin/env python3
"""PreToolUse hook: block ``studio.pipeline render``/``publish`` when the episode's
``state.json`` is missing the required gate approval.

Thin entrypoint — all logic (and its tests) live in ``studio/hooks.py``.
Reads the tool-call event as JSON on stdin; exits 2 (with a reason on stderr) to
block, 0 to allow.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio.hooks import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["gate"]))
