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
