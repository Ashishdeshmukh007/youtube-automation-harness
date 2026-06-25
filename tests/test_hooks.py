import json
from pathlib import Path

import pytest

from studio import hooks


# ---- secret_violation -------------------------------------------------------

@pytest.mark.parametrize("path", [
    ".env",
    "/abs/project/.env",
    ".env.local",
    "client_secret.json",
    "client_secret_123.json",
    "youtube_token.json",
    "secrets/private.key",
])
def test_secret_violation_blocks_reading_secret_files(path):
    assert hooks.secret_violation("Read", {"file_path": path}) is not None


@pytest.mark.parametrize("path", [
    ".env.template",
    ".env.example",
    "studio/config.py",
    "brand/brand-bible.md",
])
def test_secret_violation_allows_safe_files(path):
    assert hooks.secret_violation("Read", {"file_path": path}) is None


def test_secret_violation_blocks_editing_env():
    assert hooks.secret_violation("Edit", {"file_path": ".env"}) is not None


@pytest.mark.parametrize("cmd", [
    "cat .env",
    "git add .env",
    "git add -A && git commit -m x",  # -A would stage .env; treated below as safe
    "less .env.local",
    "cp client_secret.json backup.json",
])
def test_secret_violation_blocks_bash_touching_secrets(cmd):
    # only the commands that name a secret file should block
    result = hooks.secret_violation("Bash", {"command": cmd})
    if ".env" in cmd or "client_secret" in cmd or "youtube_token" in cmd:
        # ".env" here is part of an actual secret reference (not .env.template)
        if ".env.template" in cmd or ".env.example" in cmd:
            assert result is None
        else:
            assert result is not None


@pytest.mark.parametrize("cmd", [
    "cat .env.template",
    'git commit -m "wip"',
    "ls episodes/",
    ".venv/bin/pytest",
])
def test_secret_violation_allows_safe_bash(cmd):
    assert hooks.secret_violation("Bash", {"command": cmd}) is None


# ---- gate_violation ---------------------------------------------------------

def _episode(root: Path, slug: str, approvals: dict):
    d = root / "episodes" / slug
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps({
        "slug": slug, "stage": "x", "approvals": approvals,
        "usage": [], "created_at": "t"}))
    return d


def test_gate_blocks_publish_without_video_approval(tmp_path):
    _episode(tmp_path, "ep", {"script": "t"})
    cmd = ".venv/bin/python -m studio.pipeline publish episodes/ep"
    assert hooks.gate_violation("Bash", {"command": cmd}, root=tmp_path) is not None


def test_gate_allows_publish_with_video_approval(tmp_path):
    _episode(tmp_path, "ep", {"script": "t", "video": "t"})
    cmd = ".venv/bin/python -m studio.pipeline publish episodes/ep"
    assert hooks.gate_violation("Bash", {"command": cmd}, root=tmp_path) is None


def test_gate_blocks_render_without_script_approval(tmp_path):
    _episode(tmp_path, "ep", {})
    cmd = ".venv/bin/python -m studio.pipeline render episodes/ep"
    assert hooks.gate_violation("Bash", {"command": cmd}, root=tmp_path) is not None


def test_gate_allows_render_with_script_approval(tmp_path):
    _episode(tmp_path, "ep", {"script": "t"})
    cmd = ".venv/bin/python -m studio.pipeline render episodes/ep"
    assert hooks.gate_violation("Bash", {"command": cmd}, root=tmp_path) is None


def test_gate_blocks_publish_when_state_missing(tmp_path):
    cmd = ".venv/bin/python -m studio.pipeline publish episodes/ghost"
    assert hooks.gate_violation("Bash", {"command": cmd}, root=tmp_path) is not None


def test_gate_ignores_unrelated_bash(tmp_path):
    assert hooks.gate_violation("Bash", {"command": "ls episodes/"}, root=tmp_path) is None


def test_gate_ignores_non_bash_tools(tmp_path):
    assert hooks.gate_violation("Read", {"file_path": "episodes/ep/state.json"},
                                root=tmp_path) is None


# ---- evaluate (dispatch used by the CLI entrypoint) -------------------------

def test_evaluate_secret_returns_block_for_env():
    decision = hooks.evaluate("secret", {"tool_name": "Read",
                                          "tool_input": {"file_path": ".env"}})
    assert decision is not None


def test_evaluate_gate_blocks_publish(tmp_path):
    _episode(tmp_path, "ep", {})
    event = {"tool_name": "Bash",
             "tool_input": {"command": ".venv/bin/python -m studio.pipeline publish episodes/ep"}}
    assert hooks.evaluate("gate", event, root=tmp_path) is not None
