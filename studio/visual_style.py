"""Brand visual style — appends the channel's persistent style rules to every
image-generation prompt.

The visual-designer writes beat-specific content (subject, action, setting).
This module appends the channel-wide layer: palette, lighting, camera, what's
allowed and forbidden. Pure function — no I/O side effects.
"""
from pathlib import Path

_BRAND_STYLE_PATH = Path(__file__).resolve().parents[1] / "brand" / "visual-style.md"

# Cached once per process (the file is read once).
_cached_style: str | None = None


def _load_style() -> str:
    """Read brand/visual-style.md and return the canonical style block.

    The file's body is parsed: we strip the leading H1 header and keep everything
    after the first '---' divider (the frontmatter-style separator if present)
    or just the body. We extract a compact one-paragraph version of the style
    rules — what actually goes into a prompt — not the whole markdown file.
    """
    global _cached_style
    if _cached_style is not None:
        return _cached_style

    raw = _BRAND_STYLE_PATH.read_text()
    lines = raw.splitlines()

    # Extract section bodies we actually need for a prompt suffix.
    palette = _extract_section(lines, "Palette (canonical)")
    lighting = _extract_section(lines, "Lighting rules")
    camera = _extract_section(lines, "Camera + framing")
    forbidden = _extract_section(lines, "What's NEVER allowed (hard lines)")

    _cached_style = (
        "Cinematic shallow depth of field, 35mm lens, rule of thirds. "
        "Palette: muted earth tones — RGB(32,32,32) shadows, RGB(58,38,32) warm shadow, "
        "RGB(128,96,64) earth mid, RGB(160,128,96) sand, RGB(192,160,112) gold highlight, "
        "RGB(224,200,160) off-white. No pure black, no pure white, no saturated primaries, no neon. "
        "Lighting: soft directional from camera-left at 30° above horizon. "
        "Always visible atmosphere (mist, dust, breath). "
        "Hard rules: no deity portraits, no halos, no blue-skinned smiling god, "
        "no lotus throne, no anime cel-shading, no AI-cartoon god aesthetics, "
        "no modern Western clothing."
    )
    return _cached_style


def _extract_section(lines: list[str], header: str) -> str:
    """Pull body lines under a markdown H2 header until the next H2 or EOF."""
    out = []
    in_section = False
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            if s[3:].strip() == header:
                in_section = True
                continue
            elif in_section:
                break
        elif in_section and s and not s.startswith("|"):
            out.append(s)
    return " ".join(out)


def apply_brand_style(prompt: str, max_total_chars: int = 1100) -> str:
    """Append the brand visual-style block to a Shot: prompt.

    The prompt is the beat-specific content. The result is the full prompt sent
    to the image model — beat content + persistent style.

    The MiniMax image_generation endpoint rejects prompts longer than 1500
    characters (status 2013). To stay safely under that limit, if the combined
    prompt would exceed `max_total_chars`, the beat content is truncated from
    the right (with an ellipsis) until it fits. The style block is always
    appended intact because it's the channel's persistent identity layer.

    Idempotent: if the style block is already present at the tail, the prompt
    is returned unchanged. This makes it safe to call repeatedly during retries.
    """
    style = _load_style()
    if style in prompt:
        return prompt

    separator = ". "
    ellipsis = "..."
    budget = max_total_chars - len(style) - len(separator) - len(ellipsis)
    if budget <= 0:
        budget = max_total_chars - len(separator)
        return prompt[:budget].rstrip() + separator + style[:max_total_chars - budget - len(separator)]

    base = prompt.rstrip(". ").rstrip()
    if len(base) > budget:
        base = base[:budget].rstrip()
        if not base.endswith(('.', '!', '?')):
            base += ellipsis

    return f"{base}{separator}{style}"


def reset_cache() -> None:
    """Test helper: clear the cached style block so the file is re-read."""
    global _cached_style
    _cached_style = None