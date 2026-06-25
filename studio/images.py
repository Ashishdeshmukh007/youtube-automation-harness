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
