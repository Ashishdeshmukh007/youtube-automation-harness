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
