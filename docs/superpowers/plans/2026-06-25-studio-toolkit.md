# Studio Production Toolkit — Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic `studio/` engine that turns an approved `script.md` into a rendered, uploadable YouTube video, driven by a state machine and provider-agnostic MiniMax adapters.

**Architecture:** A Python package `studio/` with: a pure state machine (`state.py`) that owns `episode/state.json` and enforces the three gates; thin media adapters (`tts.py`, `images.py`, `music.py`, `captions.py`, `assemble.py`, `thumbnail.py`, `upload.py`) behind stable interfaces with a MiniMax default in `providers/minimax.py`; a Stage-0 `verify_credentials.py`; and a `pipeline.py` CLI that orchestrates stages. External calls are isolated in adapters so the testable logic (state transitions, request building, ffmpeg arg construction, SRT formatting) is unit-tested with mocks.

**Tech Stack:** Python 3.11+, pytest + pytest-mock, `requests`, `python-dotenv`, `Pillow`, `faster-whisper`, `google-api-python-client` + `google-auth-oauthlib`, system `ffmpeg`.

---

## Shared contracts (read before any task)

These names are used across tasks — keep them identical.

**Pipeline stages** (`studio/state.py`, `class Stage(str, Enum)`):
`PROPOSED, SCRIPT_DRAFT, SCRIPT_APPROVED, RENDERING, RENDER_REVIEW, APPROVED, PUBLISHING, PUBLISHED`

**Gates** (keys in `state.json["approvals"]`): `"topic"`, `"script"`, `"video"` → each maps to an ISO-8601 timestamp string when approved, else absent.

**Episode folder** (relative to repo root): `episodes/<slug>/` containing
`state.json, topic.md, script.md, voiceover.wav, music.wav, shots/, captions.srt, thumb.png, metadata.json, video.mp4`.

**`state.json` shape:**
```json
{
  "slug": "2026-06-25-amor-fati",
  "stage": "script_draft",
  "approvals": {"topic": "2026-06-25T10:00:00"},
  "usage": [],
  "created_at": "2026-06-25T09:55:00"
}
```

**Settings keys** (`studio/config.py`, `class Settings`): `minimax_api_key, minimax_host, minimax_group_id, voice_id, tts_model, image_model, music_model, youtube_client_secret, youtube_token`.

**Adapter return type** (`studio/types.py`, `@dataclass MediaResult`): `path: Path`, `usage: dict` (free-form provider usage, e.g. `{"characters": 1234}`).

---

## Task 0: Project scaffolding

**Files:**
- Create: `requirements.txt`, `pyproject.toml`, `.env.template`, `studio/__init__.py`, `studio/providers/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create `requirements.txt`**

```
requests==2.32.3
python-dotenv==1.0.1
Pillow==10.4.0
faster-whisper==1.0.3
google-api-python-client==2.149.0
google-auth-oauthlib==1.2.1
pytest==8.3.3
pytest-mock==3.14.0
```

- [ ] **Step 2: Create `pyproject.toml`** (pytest config + package discovery)

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-youtube-studio"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
include = ["studio*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 3: Create `.env.template`**

```
# MiniMax (Token Plan — Plus). Subscription key + host, NOT a PAYG key.
MINIMAX_API_KEY=
MINIMAX_HOST=https://api.minimax.io
MINIMAX_GROUP_ID=
MINIMAX_VOICE_ID=
MINIMAX_TTS_MODEL=speech-2.8-hd
MINIMAX_IMAGE_MODEL=image-01
MINIMAX_MUSIC_MODEL=music-2.6

# YouTube Data API v3 (OAuth)
YOUTUBE_CLIENT_SECRET=client_secret.json
YOUTUBE_TOKEN=youtube_token.json
```

- [ ] **Step 4: Create empty package files**

Create `studio/__init__.py`, `studio/providers/__init__.py`, `tests/__init__.py` (all empty).

- [ ] **Step 5: Create `tests/conftest.py`** (shared fixture: a temp episode dir)

```python
import json
from pathlib import Path
import pytest


@pytest.fixture
def episode_dir(tmp_path: Path) -> Path:
    d = tmp_path / "episodes" / "2026-06-25-test"
    (d / "shots").mkdir(parents=True)
    return d


@pytest.fixture
def state_file(episode_dir: Path) -> Path:
    sf = episode_dir / "state.json"
    sf.write_text(json.dumps({
        "slug": "2026-06-25-test",
        "stage": "proposed",
        "approvals": {},
        "usage": [],
        "created_at": "2026-06-25T09:00:00",
    }))
    return sf
```

- [ ] **Step 6: Set up venv and install**

Run:
```bash
cd "/Users/ashishdeshmukh/projects/Youtube Channel"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```
Expected: installs succeed; `.venv/bin/pytest --version` prints a version.

- [ ] **Step 7: Verify ffmpeg present**

Run: `ffmpeg -version | head -1`
Expected: prints a version line. If "command not found", run `brew install ffmpeg` first.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pyproject.toml .env.template studio tests
git commit -m "chore: scaffold studio package and test harness"
```

---

## Task 1: `studio/types.py` — shared dataclass

**Files:**
- Create: `studio/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from studio.types import MediaResult


def test_media_result_holds_path_and_usage():
    r = MediaResult(path=Path("/tmp/x.wav"), usage={"characters": 10})
    assert r.path == Path("/tmp/x.wav")
    assert r.usage["characters"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.types'`.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MediaResult:
    path: Path
    usage: dict = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_types.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add studio/types.py tests/test_types.py
git commit -m "feat: add MediaResult shared type"
```

---

## Task 2: `studio/config.py` — settings loader

**Files:**
- Create: `studio/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
from studio.config import load_settings


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setenv("MINIMAX_HOST", "https://api.minimax.io")
    monkeypatch.setenv("MINIMAX_VOICE_ID", "stoic_male")
    s = load_settings()
    assert s.minimax_api_key == "sk-test"
    assert s.minimax_host == "https://api.minimax.io"
    assert s.voice_id == "stoic_male"
    assert s.tts_model == "speech-2.8-hd"  # default applied


def test_load_settings_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    import pytest
    with pytest.raises(ValueError, match="MINIMAX_API_KEY"):
        load_settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    minimax_api_key: str
    minimax_host: str
    minimax_group_id: str
    voice_id: str
    tts_model: str
    image_model: str
    music_model: str
    youtube_client_secret: str
    youtube_token: str


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required env var: {name}")
    return val


def load_settings() -> Settings:
    return Settings(
        minimax_api_key=_require("MINIMAX_API_KEY"),
        minimax_host=os.getenv("MINIMAX_HOST", "https://api.minimax.io"),
        minimax_group_id=os.getenv("MINIMAX_GROUP_ID", ""),
        voice_id=os.getenv("MINIMAX_VOICE_ID", ""),
        tts_model=os.getenv("MINIMAX_TTS_MODEL", "speech-2.8-hd"),
        image_model=os.getenv("MINIMAX_IMAGE_MODEL", "image-01"),
        music_model=os.getenv("MINIMAX_MUSIC_MODEL", "music-2.6"),
        youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", "client_secret.json"),
        youtube_token=os.getenv("YOUTUBE_TOKEN", "youtube_token.json"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add studio/config.py tests/test_config.py
git commit -m "feat: add settings loader from .env"
```

---

## Task 3: `studio/state.py` — episode state machine (the gate keeper)

**Files:**
- Create: `studio/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import pytest
from studio.state import EpisodeState, Stage, GateError


def test_load_and_stage(state_file):
    st = EpisodeState.load(state_file.parent)
    assert st.stage == Stage.PROPOSED


def test_approve_topic_records_timestamp(state_file):
    st = EpisodeState.load(state_file.parent)
    st.approve("topic")
    assert "topic" in st.data["approvals"]


def test_advance_to_script_draft(state_file):
    st = EpisodeState.load(state_file.parent)
    st.set_stage(Stage.SCRIPT_DRAFT)
    reloaded = EpisodeState.load(state_file.parent)
    assert reloaded.stage == Stage.SCRIPT_DRAFT


def test_require_gate_blocks_without_approval(state_file):
    st = EpisodeState.load(state_file.parent)
    with pytest.raises(GateError, match="script"):
        st.require("script")


def test_require_gate_passes_after_approval(state_file):
    st = EpisodeState.load(state_file.parent)
    st.approve("script")
    st.require("script")  # no raise


def test_record_usage_appends(state_file):
    st = EpisodeState.load(state_file.parent)
    st.record_usage("tts", {"characters": 500})
    assert st.data["usage"][0]["stage"] == "tts"
    assert st.data["usage"][0]["characters"] == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_state.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import json
from datetime import datetime
from enum import Enum
from pathlib import Path


class Stage(str, Enum):
    PROPOSED = "proposed"
    SCRIPT_DRAFT = "script_draft"
    SCRIPT_APPROVED = "script_approved"
    RENDERING = "rendering"
    RENDER_REVIEW = "render_review"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"


class GateError(Exception):
    """Raised when an action requires an approval that has not been granted."""


class EpisodeState:
    def __init__(self, episode_dir: Path, data: dict):
        self.dir = episode_dir
        self.data = data

    @classmethod
    def load(cls, episode_dir: Path) -> "EpisodeState":
        data = json.loads((Path(episode_dir) / "state.json").read_text())
        return cls(Path(episode_dir), data)

    def save(self) -> None:
        (self.dir / "state.json").write_text(json.dumps(self.data, indent=2))

    @property
    def stage(self) -> Stage:
        return Stage(self.data["stage"])

    def set_stage(self, stage: Stage) -> None:
        self.data["stage"] = stage.value
        self.save()

    def approve(self, gate: str) -> None:
        self.data.setdefault("approvals", {})[gate] = datetime.now().isoformat(timespec="seconds")
        self.save()

    def require(self, gate: str) -> None:
        if gate not in self.data.get("approvals", {}):
            raise GateError(f"Gate not approved: {gate}")

    def record_usage(self, stage: str, usage: dict) -> None:
        entry = {"stage": stage, **usage}
        self.data.setdefault("usage", []).append(entry)
        self.save()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_state.py -v`
Expected: PASS (all 6 tests).

- [ ] **Step 5: Commit**

```bash
git add studio/state.py tests/test_state.py
git commit -m "feat: add episode state machine with gate enforcement"
```

---

## Task 4: `studio/providers/minimax.py` — request builders

**Files:**
- Create: `studio/providers/minimax.py`
- Test: `tests/test_minimax.py`

Builders are pure functions returning `(url, headers, payload)`. Network call is a separate thin `post_json` so tests never touch the network.

- [ ] **Step 1: Write the failing test**

```python
from studio.config import Settings
from studio.providers import minimax


def _settings():
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="stoic_male",
        tts_model="speech-2.8-hd", image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


def test_tts_request_shape():
    url, headers, payload = minimax.tts_request(_settings(), "Hello world")
    assert url == "https://api.minimax.io/v1/t2a_v2?GroupId=grp1"
    assert headers["Authorization"] == "Bearer sk-test"
    assert payload["model"] == "speech-2.8-hd"
    assert payload["text"] == "Hello world"
    assert payload["voice_setting"]["voice_id"] == "stoic_male"


def test_image_request_shape():
    url, headers, payload = minimax.image_request(_settings(), "a marble statue", n=3)
    assert url == "https://api.minimax.io/v1/image_generation"
    assert payload["model"] == "image-01"
    assert payload["prompt"] == "a marble statue"
    assert payload["n"] == 3


def test_music_request_shape():
    url, headers, payload = minimax.music_request(_settings(), "calm ambient", lyrics="")
    assert url == "https://api.minimax.io/v1/music_generation"
    assert payload["model"] == "music-2.6"
    assert payload["prompt"] == "calm ambient"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_minimax.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import requests
from studio.config import Settings


def _auth(s: Settings) -> dict:
    return {"Authorization": f"Bearer {s.minimax_api_key}", "Content-Type": "application/json"}


def tts_request(s: Settings, text: str, *, speed: float = 0.92, vol: float = 1.0,
                pitch: int = 0):
    url = f"{s.minimax_host}/v1/t2a_v2?GroupId={s.minimax_group_id}"
    payload = {
        "model": s.tts_model,
        "text": text,
        "voice_setting": {"voice_id": s.voice_id, "speed": speed, "vol": vol, "pitch": pitch},
        "audio_setting": {"format": "wav", "sample_rate": 44100, "channel": 1},
    }
    return url, _auth(s), payload


def image_request(s: Settings, prompt: str, *, n: int = 1, aspect_ratio: str = "16:9"):
    url = f"{s.minimax_host}/v1/image_generation"
    payload = {
        "model": s.image_model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "n": n,
        "response_format": "url",
    }
    return url, _auth(s), payload


def music_request(s: Settings, prompt: str, *, lyrics: str = ""):
    url = f"{s.minimax_host}/v1/music_generation"
    payload = {"model": s.music_model, "prompt": prompt, "lyrics": lyrics}
    return url, _auth(s), payload


def post_json(url: str, headers: dict, payload: dict, *, timeout: int = 120) -> dict:
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_minimax.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add studio/providers/minimax.py tests/test_minimax.py
git commit -m "feat: add MiniMax request builders"
```

> **Note for implementer:** Exact MiniMax payload fields (e.g. music params, image
> `response_format`) may need tuning against the live API — this is what Task 5
> (`verify_credentials.py`) confirms empirically. Keep changes inside this file.

---

## Task 5: `studio/verify_credentials.py` — Stage 0 check

**Files:**
- Create: `studio/verify_credentials.py`
- Test: `tests/test_verify_credentials.py`

- [ ] **Step 1: Write the failing test**

```python
from studio.config import Settings
from studio import verify_credentials as vc


def _settings():
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="v", tts_model="speech-2.8-hd",
        image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


def test_check_endpoint_reports_ok(mocker):
    mocker.patch("studio.providers.minimax.post_json", return_value={"base_resp": {"status_code": 0}})
    result = vc.check_endpoint("tts", _settings())
    assert result["ok"] is True


def test_check_endpoint_reports_failure(mocker):
    mocker.patch("studio.providers.minimax.post_json", side_effect=Exception("401 invalid key"))
    result = vc.check_endpoint("tts", _settings())
    assert result["ok"] is False
    assert "401" in result["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_verify_credentials.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import sys
from studio.config import Settings, load_settings
from studio.providers import minimax

_PROBES = {
    "tts": lambda s: minimax.tts_request(s, "test"),
    "image": lambda s: minimax.image_request(s, "a simple grey circle", n=1),
    "music": lambda s: minimax.music_request(s, "soft ambient pad", lyrics=""),
}


def check_endpoint(name: str, s: Settings) -> dict:
    try:
        url, headers, payload = _PROBES[name](s)
        minimax.post_json(url, headers, payload, timeout=60)
        return {"endpoint": name, "ok": True, "error": None}
    except Exception as e:  # noqa: BLE001 - report any failure to the operator
        return {"endpoint": name, "ok": False, "error": str(e)}


def main() -> int:
    s = load_settings()
    failures = 0
    for name in _PROBES:
        r = check_endpoint(name, s)
        mark = "OK " if r["ok"] else "FAIL"
        print(f"[{mark}] {name}" + ("" if r["ok"] else f" -> {r['error']}"))
        failures += 0 if r["ok"] else 1
    print(f"\n{len(_PROBES) - failures}/{len(_PROBES)} endpoints reachable.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_verify_credentials.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add studio/verify_credentials.py tests/test_verify_credentials.py
git commit -m "feat: add Stage 0 credential verification"
```

---

## Task 6: `studio/tts.py` — voiceover adapter

**Files:**
- Create: `studio/tts.py`
- Test: `tests/test_tts.py`

MiniMax T2A returns audio as a hex string in `data.audio`. The adapter decodes it to bytes and writes the wav.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from studio.config import Settings
from studio import tts


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def test_synthesize_writes_decoded_audio(tmp_path, mocker):
    fake_bytes = b"RIFFfakewav"
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"audio": fake_bytes.hex()},
        "extra_info": {"audio_length": 1000},
    })
    out = tmp_path / "voiceover.wav"
    result = tts.synthesize(_settings(), "Hello", out)
    assert out.read_bytes() == fake_bytes
    assert result.path == out
    assert result.usage["characters"] == len("Hello")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_tts.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path
from studio.config import Settings
from studio.providers import minimax
from studio.types import MediaResult


def synthesize(s: Settings, text: str, out_path: Path, *, speed: float = 0.92) -> MediaResult:
    url, headers, payload = minimax.tts_request(s, text, speed=speed)
    data = minimax.post_json(url, headers, payload)
    audio_hex = data["data"]["audio"]
    out_path.write_bytes(bytes.fromhex(audio_hex))
    return MediaResult(path=out_path, usage={"characters": len(text)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_tts.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add studio/tts.py tests/test_tts.py
git commit -m "feat: add TTS voiceover adapter"
```

---

## Task 7: `studio/images.py` — image generation adapter

**Files:**
- Create: `studio/images.py`
- Test: `tests/test_images.py`

Adapter requests N images for a list of prompts, downloads each URL to `shots/NN.png`, and writes `shots/shots.json` (prompt↔file map).

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from studio.config import Settings
from studio import images


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def test_generate_downloads_and_indexes(tmp_path, mocker):
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"image_urls": ["http://img/0.png"]},
    })
    mocker.patch("studio.images._download", side_effect=lambda url, dest: dest.write_bytes(b"PNG"))
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    result = images.generate(_settings(), ["a marble bust of Marcus Aurelius"], shots_dir)
    files = sorted(shots_dir.glob("*.png"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"PNG"
    index = json.loads((shots_dir / "shots.json").read_text())
    assert index[0]["prompt"] == "a marble bust of Marcus Aurelius"
    assert result.usage["images"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_images.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import json
from pathlib import Path
import requests
from studio.config import Settings
from studio.providers import minimax
from studio.types import MediaResult


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def generate(s: Settings, prompts: list[str], shots_dir: Path) -> MediaResult:
    shots_dir.mkdir(parents=True, exist_ok=True)
    index = []
    count = 0
    for i, prompt in enumerate(prompts):
        url, headers, payload = minimax.image_request(s, prompt, n=1)
        data = minimax.post_json(url, headers, payload)
        img_url = data["data"]["image_urls"][0]
        dest = shots_dir / f"{i:02d}.png"
        _download(img_url, dest)
        index.append({"index": i, "prompt": prompt, "file": dest.name})
        count += 1
    (shots_dir / "shots.json").write_text(json.dumps(index, indent=2))
    return MediaResult(path=shots_dir, usage={"images": count})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_images.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add studio/images.py tests/test_images.py
git commit -m "feat: add image generation adapter"
```

---

## Task 8: `studio/music.py` — music adapter

**Files:**
- Create: `studio/music.py`
- Test: `tests/test_music.py`

MiniMax music returns a hex audio string like TTS.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from studio.config import Settings
from studio import music


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def test_compose_writes_audio(tmp_path, mocker):
    raw = b"RIFFmusic"
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"audio": raw.hex()},
    })
    out = tmp_path / "music.wav"
    result = music.compose(_settings(), "slow ambient stoic pad, no drums", out)
    assert out.read_bytes() == raw
    assert result.usage["tracks"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_music.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path
from studio.config import Settings
from studio.providers import minimax
from studio.types import MediaResult


def compose(s: Settings, prompt: str, out_path: Path) -> MediaResult:
    url, headers, payload = minimax.music_request(s, prompt, lyrics="")
    data = minimax.post_json(url, headers, payload)
    out_path.write_bytes(bytes.fromhex(data["data"]["audio"]))
    return MediaResult(path=out_path, usage={"tracks": 1})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_music.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add studio/music.py tests/test_music.py
git commit -m "feat: add music composition adapter"
```

---

## Task 9: `studio/captions.py` — Whisper → SRT

**Files:**
- Create: `studio/captions.py`
- Test: `tests/test_captions.py`

Split into a pure formatter (`segments_to_srt`) that is unit-tested, and a thin `transcribe` that wraps faster-whisper.

- [ ] **Step 1: Write the failing test**

```python
from studio.captions import segments_to_srt, _ts


def test_timestamp_format():
    assert _ts(0) == "00:00:00,000"
    assert _ts(3661.5) == "01:01:01,500"


def test_segments_to_srt():
    segs = [(0.0, 1.5, "First line"), (1.5, 3.0, "Second line")]
    srt = segments_to_srt(segs)
    assert "1\n00:00:00,000 --> 00:00:01,500\nFirst line" in srt
    assert "2\n00:00:01,500 --> 00:00:03,000\nSecond line" in srt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_captions.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def segments_to_srt(segments) -> str:
    lines = []
    for i, (start, end, text) in enumerate(segments, start=1):
        lines.append(f"{i}\n{_ts(start)} --> {_ts(end)}\n{text.strip()}\n")
    return "\n".join(lines)


def transcribe(audio_path: Path, srt_path: Path, *, model_size: str = "base") -> Path:
    from faster_whisper import WhisperModel  # imported lazily; heavy dependency
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio_path), word_timestamps=False)
    tuples = [(s.start, s.end, s.text) for s in segments]
    srt_path.write_text(segments_to_srt(tuples))
    return srt_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_captions.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add studio/captions.py tests/test_captions.py
git commit -m "feat: add Whisper caption transcription with SRT formatter"
```

---

## Task 10: `studio/assemble.py` — ffmpeg arg construction + render

**Files:**
- Create: `studio/assemble.py`
- Test: `tests/test_assemble.py`

Pure `build_ffmpeg_args(...)` returns the arg list (unit-tested); `render(...)` runs it via subprocess. Visuals = each still shown for an equal slice of the voiceover with a slow Ken Burns zoom; music mixed under the voice at low volume; captions burned in.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from studio.assemble import build_ffmpeg_args


def test_build_args_includes_inputs_and_outputs(tmp_path):
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots,
        voiceover=tmp_path / "voiceover.wav",
        music=tmp_path / "music.wav",
        captions=tmp_path / "captions.srt",
        out=tmp_path / "video.mp4",
        total_seconds=20.0,
    )
    assert args[0] == "ffmpeg"
    assert "-y" in args
    # both stills are inputs
    assert str(shots[0]) in args and str(shots[1]) in args
    # voiceover and music inputs present
    assert str(tmp_path / "voiceover.wav") in args
    assert str(tmp_path / "music.wav") in args
    # subtitle filter references the srt
    joined = " ".join(args)
    assert "subtitles=" in joined
    assert args[-1] == str(tmp_path / "video.mp4")


def test_per_shot_duration_is_total_over_count(tmp_path):
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        captions=tmp_path / "c.srt", out=tmp_path / "o.mp4", total_seconds=20.0,
    )
    joined = " ".join(args)
    assert "d=250" in joined  # 10s per shot * 25 fps = 250 frames
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_assemble.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import subprocess
from pathlib import Path

FPS = 25
W, H = 1920, 1080


def build_ffmpeg_args(*, shots: list[Path], voiceover: Path, music: Path,
                      captions: Path, out: Path, total_seconds: float) -> list[str]:
    n = len(shots)
    per_shot = total_seconds / n
    frames = int(round(per_shot * FPS))

    args: list[str] = ["ffmpeg", "-y"]
    # image inputs (looped to the per-shot duration)
    for sh in shots:
        args += ["-loop", "1", "-t", f"{per_shot:.3f}", "-i", str(sh)]
    # audio inputs
    args += ["-i", str(voiceover), "-i", str(music)]

    # per-image Ken Burns zoom, then concat
    filters = []
    for i in range(n):
        filters.append(
            f"[{i}:v]scale={W}:-2,zoompan=z='min(zoom+0.0005,1.15)':"
            f"d={frames}:s={W}x{H}:fps={FPS}[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(n))
    filters.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vcat]")
    # burn captions
    filters.append(f"[vcat]subtitles={captions}[vout]")
    # mix: voiceover full, music ducked to 0.18
    va, ma = n, n + 1  # audio input indices
    filters.append(
        f"[{ma}:a]volume=0.18[mlow];"
        f"[{va}:a][mlow]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )

    args += ["-filter_complex", ";".join(filters)]
    args += ["-map", "[vout]", "-map", "[aout]"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)]
    return args


def render(*, shots: list[Path], voiceover: Path, music: Path, captions: Path,
           out: Path, total_seconds: float) -> Path:
    args = build_ffmpeg_args(shots=shots, voiceover=voiceover, music=music,
                             captions=captions, out=out, total_seconds=total_seconds)
    subprocess.run(args, check=True)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_assemble.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add studio/assemble.py tests/test_assemble.py
git commit -m "feat: add ffmpeg assembly with Ken Burns, music duck, burned captions"
```

---

## Task 11: `studio/thumbnail.py` — Pillow text overlay

**Files:**
- Create: `studio/thumbnail.py`
- Test: `tests/test_thumbnail.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from PIL import Image
from studio.thumbnail import compose


def test_compose_produces_1280x720(tmp_path):
    base = tmp_path / "base.png"
    Image.new("RGB", (1920, 1080), (20, 20, 30)).save(base)
    out = tmp_path / "thumb.png"
    compose(base, "AMOR FATI", out)
    img = Image.open(out)
    assert img.size == (1280, 720)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_thumbnail.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def compose(base_image: Path, title: str, out_path: Path) -> Path:
    img = Image.open(base_image).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img)
    # darken lower third for legibility
    overlay = Image.new("RGB", (W, H // 3), (0, 0, 0))
    img.paste(Image.blend(img.crop((0, H - H // 3, W, H)), overlay, 0.55), (0, H - H // 3))
    font = _font(96)
    text = title.upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, H - H // 3 + 30), text, font=font, fill=(240, 230, 210))
    img.save(out_path)
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_thumbnail.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add studio/thumbnail.py tests/test_thumbnail.py
git commit -m "feat: add thumbnail compositor"
```

---

## Task 12: `studio/upload.py` — YouTube upload

**Files:**
- Create: `studio/upload.py`
- Test: `tests/test_upload.py`

Pure `build_body(metadata)` is unit-tested; `upload(...)` wraps the Google client (mocked in tests). Default visibility `private` unless metadata says otherwise.

- [ ] **Step 1: Write the failing test**

```python
from studio.upload import build_body


def test_build_body_defaults_to_private():
    meta = {"title": "Amor Fati", "description": "On loving fate",
            "tags": ["stoicism", "philosophy"]}
    body = build_body(meta)
    assert body["snippet"]["title"] == "Amor Fati"
    assert body["snippet"]["tags"] == ["stoicism", "philosophy"]
    assert body["status"]["privacyStatus"] == "private"


def test_build_body_respects_visibility_and_schedule():
    meta = {"title": "T", "description": "D", "tags": [],
            "visibility": "public", "publish_at": "2026-07-01T12:00:00Z"}
    body = build_body(meta)
    assert body["status"]["privacyStatus"] == "public"
    assert body["status"]["publishAt"] == "2026-07-01T12:00:00Z"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_upload.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def build_body(meta: dict) -> dict:
    status = {"privacyStatus": meta.get("visibility", "private"),
              "selfDeclaredMadeForKids": False}
    if meta.get("publish_at"):
        status["publishAt"] = meta["publish_at"]
        status["privacyStatus"] = "private"  # required by API when scheduling
        if meta.get("visibility") == "public":
            status["privacyStatus"] = "public"
    return {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "22"),
        },
        "status": status,
    }


def _service(client_secret: str, token: str):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if Path(token).exists():
        creds = Credentials.from_authorized_user_file(token, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(token).write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(video: Path, thumb: Path, meta: dict, *, client_secret: str, token: str) -> str:
    from googleapiclient.http import MediaFileUpload
    service = _service(client_secret, token)
    request = service.videos().insert(
        part="snippet,status", body=build_body(meta),
        media_body=MediaFileUpload(str(video), resumable=True),
    )
    response = request.execute()
    video_id = response["id"]
    if thumb and Path(thumb).exists():
        service.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb))).execute()
    return video_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_upload.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add studio/upload.py tests/test_upload.py
git commit -m "feat: add YouTube upload adapter"
```

---

## Task 13: `studio/pipeline.py` — orchestration + CLI + walking skeleton

**Files:**
- Create: `studio/pipeline.py`
- Test: `tests/test_pipeline.py`

`render_episode` runs voice→images→music→captions→assembly→thumbnail, enforcing the `script` gate first and advancing state to `RENDER_REVIEW`. `publish_episode` enforces the `video` gate, uploads, advances to `PUBLISHED`. The test mocks every adapter so it verifies orchestration + gates + state, not real media.

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
import pytest
from studio.state import EpisodeState, Stage, GateError
from studio import pipeline


def _seed(dir: Path, stage: str, approvals: dict):
    (dir / "shots").mkdir(parents=True, exist_ok=True)
    (dir / "state.json").write_text(json.dumps({
        "slug": "ep", "stage": stage, "approvals": approvals,
        "usage": [], "created_at": "2026-06-25T09:00:00"}))
    (dir / "script.md").write_text("Shot: a statue.\nShot: a mountain.")


def test_render_requires_script_gate(tmp_path):
    _seed(tmp_path, "script_draft", {})  # no script approval
    with pytest.raises(GateError, match="script"):
        pipeline.render_episode(tmp_path, settings=None)


def test_render_runs_all_stages_and_advances(tmp_path, mocker):
    _seed(tmp_path, "script_approved", {"script": "2026-06-25T10:00:00"})
    mocker.patch("studio.pipeline.load_settings", return_value=object())
    mocker.patch("studio.pipeline.tts.synthesize",
                 return_value=mocker.Mock(usage={"characters": 5}))
    mocker.patch("studio.pipeline.images.generate",
                 return_value=mocker.Mock(usage={"images": 2}))
    mocker.patch("studio.pipeline.music.compose",
                 return_value=mocker.Mock(usage={"tracks": 1}))
    mocker.patch("studio.pipeline.captions.transcribe")
    mocker.patch("studio.pipeline._voiceover_seconds", return_value=20.0)
    mocker.patch("studio.pipeline._image_files", return_value=[tmp_path / "shots" / "00.png"])
    mocker.patch("studio.pipeline.assemble.render")
    mocker.patch("studio.pipeline.thumbnail.compose")
    pipeline.render_episode(tmp_path, settings=None)
    st = EpisodeState.load(tmp_path)
    assert st.stage == Stage.RENDER_REVIEW
    assert any(u["stage"] == "tts" for u in st.data["usage"])


def test_publish_requires_video_gate(tmp_path):
    _seed(tmp_path, "render_review", {"script": "t"})  # no video approval
    with pytest.raises(GateError, match="video"):
        pipeline.publish_episode(tmp_path, settings=None)


def test_publish_uploads_and_advances(tmp_path, mocker):
    _seed(tmp_path, "approved", {"script": "t", "video": "t"})
    (tmp_path / "metadata.json").write_text(json.dumps(
        {"title": "T", "description": "D", "tags": []}))
    (tmp_path / "video.mp4").write_bytes(b"v")
    (tmp_path / "thumb.png").write_bytes(b"t")
    mocker.patch("studio.pipeline.load_settings", return_value=mocker.Mock(
        youtube_client_secret="cs", youtube_token="tok"))
    mocker.patch("studio.pipeline.upload.upload", return_value="VIDEOID123")
    vid = pipeline.publish_episode(tmp_path, settings=None)
    assert vid == "VIDEOID123"
    assert EpisodeState.load(tmp_path).stage == Stage.PUBLISHED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pipeline.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from studio.config import load_settings
from studio.state import EpisodeState, Stage
from studio import tts, images, music, captions, assemble, thumbnail, upload


def _script_shots(script_path: Path) -> tuple[str, list[str]]:
    """Return (narration_text, image_prompts). Lines starting 'Shot:' are visual
    prompts; everything else is narration."""
    narration, prompts = [], []
    for line in script_path.read_text().splitlines():
        if line.strip().lower().startswith("shot:"):
            prompts.append(line.split(":", 1)[1].strip())
        elif line.strip():
            narration.append(line.strip())
    if not prompts:
        prompts = ["a cinematic marble statue, dramatic light, dark background"]
    return " ".join(narration), prompts


def _voiceover_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _image_files(shots_dir: Path) -> list[Path]:
    return sorted(shots_dir.glob("[0-9][0-9].png"))


def render_episode(episode_dir: Path, settings=None) -> None:
    episode_dir = Path(episode_dir)
    st = EpisodeState.load(episode_dir)
    st.require("script")
    st.set_stage(Stage.RENDERING)
    s = settings or load_settings()

    narration, prompts = _script_shots(episode_dir / "script.md")

    vo = tts.synthesize(s, narration, episode_dir / "voiceover.wav")
    st.record_usage("tts", vo.usage)

    im = images.generate(s, prompts, episode_dir / "shots")
    st.record_usage("images", im.usage)

    mu = music.compose(s, "slow ambient stoic pad, no percussion, contemplative",
                       episode_dir / "music.wav")
    st.record_usage("music", mu.usage)

    captions.transcribe(episode_dir / "voiceover.wav", episode_dir / "captions.srt")

    total = _voiceover_seconds(episode_dir / "voiceover.wav")
    shot_files = _image_files(episode_dir / "shots")
    assemble.render(
        shots=shot_files, voiceover=episode_dir / "voiceover.wav",
        music=episode_dir / "music.wav", captions=episode_dir / "captions.srt",
        out=episode_dir / "video.mp4", total_seconds=total)

    thumbnail.compose(shot_files[0], _title_from(episode_dir),
                      episode_dir / "thumb.png")

    st.set_stage(Stage.RENDER_REVIEW)


def _title_from(episode_dir: Path) -> str:
    topic = episode_dir / "topic.md"
    if topic.exists():
        first = topic.read_text().strip().splitlines()[0]
        return re.sub(r"^#+\s*", "", first)[:60] or episode_dir.name
    return episode_dir.name


def publish_episode(episode_dir: Path, settings=None) -> str:
    episode_dir = Path(episode_dir)
    st = EpisodeState.load(episode_dir)
    st.require("video")
    st.set_stage(Stage.PUBLISHING)
    s = settings or load_settings()
    meta = json.loads((episode_dir / "metadata.json").read_text())
    video_id = upload.upload(
        episode_dir / "video.mp4", episode_dir / "thumb.png", meta,
        client_secret=s.youtube_client_secret, token=s.youtube_token)
    st.data["youtube_video_id"] = video_id
    st.set_stage(Stage.PUBLISHED)
    return video_id


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("render", "publish"):
        p = sub.add_parser(name)
        p.add_argument("episode_dir")
    args = parser.parse_args(argv)
    if args.cmd == "render":
        render_episode(Path(args.episode_dir))
    else:
        print(publish_episode(Path(args.episode_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_pipeline.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: ALL tests pass.

- [ ] **Step 6: Commit**

```bash
git add studio/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestration with gate-enforced render and publish"
```

---

## Task 14: Live smoke test (manual, requires real keys)

**Files:** none (operator runs against the live API once credentials exist).

- [ ] **Step 1: Fill `.env`** from `.env.template` with the real MiniMax subscription key, host, group id, and chosen voice id.

- [ ] **Step 2: Run Stage 0**

Run: `.venv/bin/python -m studio.verify_credentials`
Expected: `3/3 endpoints reachable.` If any FAIL, fix the key/host/payload in `providers/minimax.py` before continuing. **Do not proceed past a failing Stage 0.**

- [ ] **Step 3: Create a tiny test episode** by hand:

```bash
mkdir -p episodes/smoke/shots
printf '%s\n' '{"slug":"smoke","stage":"script_approved","approvals":{"script":"now"},"usage":[],"created_at":"now"}' > episodes/smoke/state.json
printf '# Amor Fati\n' > episodes/smoke/topic.md
printf 'Shot: a marble statue lit dramatically.\nAmor fati means to love one'\''s fate.\nShot: a lone mountain at dawn.\nAccept what is, and find freedom in it.\n' > episodes/smoke/script.md
```

- [ ] **Step 4: Render**

Run: `.venv/bin/python -m studio.pipeline render episodes/smoke`
Expected: produces `episodes/smoke/video.mp4`, `thumb.png`, `captions.srt`; state becomes `render_review`. Open `video.mp4` and confirm voice + visuals + music + captions are present.

- [ ] **Step 5: Approve video gate + add metadata, then publish (unlisted)**

```bash
printf '%s\n' '{"title":"Amor Fati — smoke test","description":"test","tags":["stoicism"],"visibility":"unlisted"}' > episodes/smoke/metadata.json
python - <<'PY'
import json,sys
from pathlib import Path
d=Path("episodes/smoke/state.json"); s=json.loads(d.read_text())
s["approvals"]["video"]="now"; s["stage"]="approved"; d.write_text(json.dumps(s))
PY
.venv/bin/python -m studio.pipeline publish episodes/smoke
```
Expected: prints a YouTube video id; the video appears **unlisted** on the channel; `state.json` stage is `published`. (First run opens a browser for one-time YouTube OAuth.)

- [ ] **Step 6: Clean up the smoke episode**

```bash
rm -rf episodes/smoke
```

This task has no automated commit — it is a manual verification gate confirming the engine works end-to-end against live services before Plan 2 wraps it in the harness.

---

## Self-Review (completed)

- **Spec coverage:** state machine + 3 gates (Task 3, 13), MiniMax adapters TTS/image/music (4,6,7,8), Stage 0 (5), captions (9), ffmpeg assembly with Ken Burns/duck/captions (10), thumbnail (11), YouTube upload private-default (12), pipeline CLI + walking skeleton (13,14), provider-agnostic interfaces (adapters take `Settings`, MiniMax isolated in `providers/`). Phase-2 items (Hailuo video, cron, analytics) intentionally excluded.
- **Placeholder scan:** none — every code step has full code; the one "tune payload" note (Task 4) is bounded to a single file and resolved empirically in Task 14 Step 2.
- **Type consistency:** `Settings` field order matches `config.py` constructor across all adapter tests; `MediaResult(path, usage)` used uniformly; `Stage` values match `state.json` strings; `EpisodeState` methods (`load/require/approve/set_stage/record_usage`) consistent between Task 3 and Task 13.
```
