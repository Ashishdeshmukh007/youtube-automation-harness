from pathlib import Path
from studio.config import Settings
from studio.providers import minimax
from studio.types import MediaResult


def compose(s: Settings, prompt: str, out_path: Path) -> MediaResult:
    url, headers, payload = minimax.music_request(s, prompt, lyrics="")
    data = minimax.post_json(url, headers, payload)
    out_path.write_bytes(bytes.fromhex(data["data"]["audio"]))
    return MediaResult(path=out_path, usage={"tracks": 1})
