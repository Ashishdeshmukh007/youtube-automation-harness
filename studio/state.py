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
