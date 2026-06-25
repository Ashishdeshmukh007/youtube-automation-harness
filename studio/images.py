import json
from pathlib import Path
import requests
from studio.config import Settings
from studio.providers import minimax
from studio.types import MediaResult
from studio import characters as _characters
from studio import visual_style as _visual_style


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def _expand_prompt(prompt: str) -> str:
    """Apply the brand character library and visual-style to a prompt.

    Order matters: character expansion happens first (so the canonical
    description is appended after the beat-specific subject), then visual
    style is appended at the tail (so the style block is the final layer
    the model sees — most influential position in diffusion prompts).
    """
    return _visual_style.apply_brand_style(_characters.expand_prompt(prompt))


def generate(s: Settings, prompts: list[str], shots_dir: Path) -> MediaResult:
    shots_dir.mkdir(parents=True, exist_ok=True)
    index = []
    count = 0
    chars_used: set[str] = set()
    for i, prompt in enumerate(prompts):
        expanded = _expand_prompt(prompt)
        # If the beat names a recurring character, condition the generation on its
        # locked reference portrait so the face/clothing stay consistent across
        # shots and episodes. image-01 anchors one subject, so for multi-character
        # beats we anchor the first detected (primary) character.
        subject_reference = None
        primary = _characters.primary_character(prompt)
        if primary:
            uri = _characters.reference_data_uri(primary)
            if uri:
                subject_reference = [{"type": "character", "image_file": uri}]
        url, headers, payload = minimax.image_request(
            s, expanded, n=1, subject_reference=subject_reference)
        data = minimax.post_json(url, headers, payload)
        if not data.get("data") or not data.get("data", {}).get("image_urls"):
            raise RuntimeError(
                f"image_generation failed for shot {i:02d}: "
                f"status={data.get('base_resp', {}).get('status_msg')}, "
                f"prompt_len={len(expanded)}, "
                f"prompt_preview={expanded[:100]!r}"
            )
        img_url = data["data"]["image_urls"][0]
        dest = shots_dir / f"{i:02d}.png"
        _download(img_url, dest)
        index.append({"index": i, "prompt": prompt, "file": dest.name})
        chars_used.update(_characters.detect_characters(prompt))
        count += 1
    (shots_dir / "shots.json").write_text(json.dumps(index, indent=2))
    return MediaResult(path=shots_dir, usage={
        "images": count,
        "characters_used": sorted(chars_used),
    })
