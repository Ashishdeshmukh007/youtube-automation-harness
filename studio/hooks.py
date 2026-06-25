"""Deterministic PreToolUse guards for the harness.

Two guards, both defense-in-depth (the studio engine also enforces gates):

- ``secret`` — block reading/editing/committing secret files (`.env`, keys, OAuth).
- ``gate`` — block ``studio.pipeline render``/``publish`` unless ``state.json`` records
  the required prior approval.

The pure functions here are unit-tested; ``main`` is the thin stdin/exit-code shim
that Claude Code invokes via ``.claude/hooks/*``.
"""
import json
import re
import sys
from pathlib import Path

# Files that must never be read, edited, or committed.
_SECRET_NAMES = {".env", ".env.local", "youtube_token.json"}
_SECRET_PATTERNS = (
    re.compile(r"(^|/)client_secret[^/]*\.json$"),
    re.compile(r"\.key$"),
)
# A `.env` reference that is NOT a safe template/example.
_ENV_REF = re.compile(r"\.env(?!\.template|\.example)(?![\w])")
_SECRET_IN_CMD = re.compile(r"client_secret[\w-]*\.json|youtube_token\.json|[\w./-]+\.key\b")

# `studio.pipeline render|publish <episode_dir>` and the gate each needs.
_PIPELINE = re.compile(r"studio\.pipeline\s+(render|publish)\s+(\S+)")
_REQUIRED_GATE = {"render": "script", "publish": "video"}


def _path_is_secret(path: str) -> bool:
    name = Path(path).name
    if name in _SECRET_NAMES:
        return True
    return any(p.search(path) for p in _SECRET_PATTERNS)


def _command_touches_secret(command: str) -> bool:
    return bool(_ENV_REF.search(command) or _SECRET_IN_CMD.search(command))


def secret_violation(tool_name: str, tool_input: dict) -> str | None:
    """Return a block reason if the tool call would touch a secret file."""
    if tool_name in ("Read", "Edit", "Write"):
        path = tool_input.get("file_path", "")
        if path and _path_is_secret(path):
            return (f"secret-guard: refusing to access secret file '{path}'. "
                    "Secrets live in .env and are off-limits; never read or commit them.")
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if command and _command_touches_secret(command):
            return ("secret-guard: this command references a secret file (.env / key / "
                    "OAuth json). Never read, print, or commit secrets.")
    return None


def gate_violation(tool_name: str, tool_input: dict, *, root: Path = Path(".")) -> str | None:
    """Return a block reason if a pipeline render/publish lacks its required gate."""
    if tool_name != "Bash":
        return None
    m = _PIPELINE.search(tool_input.get("command", ""))
    if not m:
        return None
    action, episode_path = m.group(1), m.group(2)
    gate = _REQUIRED_GATE[action]
    state_file = Path(root) / episode_path / "state.json"
    if not state_file.exists():
        return (f"gate-guard: {state_file} not found — cannot {action} an episode "
                "with no state. The gate is unverifiable.")
    approvals = json.loads(state_file.read_text()).get("approvals", {})
    if gate not in approvals:
        return (f"gate-guard: '{action}' requires the '{gate}' gate, which is not "
                f"approved in {state_file}. Get the owner's approval first — do not "
                "work around the gate.")
    return None


def evaluate(guard: str, event: dict, *, root: Path = Path(".")) -> str | None:
    """Dispatch a parsed hook event to the named guard. Returns block reason or None."""
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    if guard == "secret":
        return secret_violation(tool_name, tool_input)
    if guard == "gate":
        return gate_violation(tool_name, tool_input, root=root)
    raise ValueError(f"unknown guard: {guard}")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    guard = argv[0] if argv else ""
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # no parseable event → don't block
    reason = evaluate(guard, event)
    if reason:
        print(reason, file=sys.stderr)
        return 2  # PreToolUse: exit 2 blocks the call, stderr is shown to the agent
    return 0


if __name__ == "__main__":
    sys.exit(main())
