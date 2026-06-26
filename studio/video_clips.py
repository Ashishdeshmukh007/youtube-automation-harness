"""Image-to-video — animate a still into a short cinematic clip via fal.ai (Wan
2.2). Used for the hybrid pipeline's 'hero' beats; other beats stay stills.
"""
import base64
import io
from pathlib import Path

import requests
from PIL import Image

from studio.providers import fal


def _data_uri(image_path: Path, max_px: int = 1024) -> str:
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def animate(fal_key: str, image_path: Path, prompt: str, out_path: Path) -> Path:
    """Animate `image_path` into a clip at `out_path` using the still as the first
    frame. Blocks until the fal job completes (~1 min per clip)."""
    url, headers, payload = fal.i2v_request(fal_key, _data_uri(image_path), prompt)
    sub = fal.submit(url, headers, payload)
    fal.poll_until_done(sub["status_url"], headers)
    result = fal.get_result(sub["response_url"], headers)
    video_url = fal.result_video_url(result)
    if not video_url:
        raise RuntimeError(f"fal returned no video url: {result}")
    _download(video_url, out_path)
    return out_path
