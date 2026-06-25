from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MediaResult:
    path: Path
    usage: dict = field(default_factory=dict)
