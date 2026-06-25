"""Character library — detects named characters in image prompts and supplies
both their canonical text description and a locked reference portrait.

Character consistency uses two layers:
  1. Text: append the same rich canonical description to every prompt that names
     the character (`expand_prompt`).
  2. Image: condition the generation on a locked reference portrait via MiniMax
     image-01 `subject_reference` (`reference_data_uri` + `primary_character`),
     so the face/clothing carry across shots and episodes. image-01 anchors one
     subject, so `primary_character` picks the figure a beat is about.

The character catalog lives in brand/characters/*.md (canonical descriptions +
prompt suffixes) alongside <name>.reference.png/.jpg (the locked portrait). Each
new character = one new .md + reference image + a catalog entry below.
"""
import base64
import re
from pathlib import Path

_CHARACTERS_DIR = Path(__file__).resolve().parents[1] / "brand" / "characters"

# Each entry: (canonical_name, detection_aliases, md_filename)
# detection_aliases are the lowercase substrings we scan for in the prompt.
_CATALOG: list[tuple[str, list[str], str]] = [
    ("Arjuna", ["arjuna"], "arjuna.md"),
    ("Krishna", ["krishna"], "krishna.md"),
]

_suffix_cache: dict[str, str] = {}
_data_uri_cache: dict[str, str] = {}


def reference_data_uri(name: str) -> str | None:
    """Return a base64 JPEG data URI for a character's locked reference portrait,
    suitable as a MiniMax `subject_reference` payload. None if the character is
    unknown or has no reference image on disk.

    Reads the downscaled `<name>.reference.jpg` (kept small for the API); the
    full-res `<name>.reference.png` is the human-facing anchor.
    """
    canonical = next((c for c, _, _ in _CATALOG if c.lower() == name.lower()), None)
    if canonical is None:
        return None
    if canonical in _data_uri_cache:
        return _data_uri_cache[canonical]
    jpg = _CHARACTERS_DIR / f"{canonical.lower()}.reference.jpg"
    if not jpg.exists():
        return None
    b64 = base64.b64encode(jpg.read_bytes()).decode()
    uri = f"data:image/jpeg;base64,{b64}"
    _data_uri_cache[canonical] = uri
    return uri


def _load_suffix(md_filename: str) -> str:
    """Read a character .md file and extract the 'Prompt suffix' block."""
    if md_filename in _suffix_cache:
        return _suffix_cache[md_filename]
    path = _CHARACTERS_DIR / md_filename
    text = path.read_text()
    # Extract the block between '## Prompt suffix' and the next '##' or EOF.
    m = re.search(
        r"##\s+Prompt suffix.*?```\n(.*?)```",
        text, re.DOTALL)
    if m:
        suffix = m.group(1).strip()
        _suffix_cache[md_filename] = suffix
        return suffix
    # Fallback: if no fenced block, take everything after the header.
    m = re.search(r"##\s+Prompt suffix(.*?)(?:\n##|\Z)", text, re.DOTALL)
    suffix = (m.group(1).strip() if m else "")
    _suffix_cache[md_filename] = suffix
    return suffix


def detect_characters(prompt: str) -> list[str]:
    """Return the canonical names of characters mentioned in the prompt."""
    text = prompt.lower()
    found = []
    for canonical, aliases, _ in _CATALOG:
        if any(alias in text for alias in aliases):
            found.append(canonical)
    return found


def primary_character(prompt: str) -> str | None:
    """The character a beat is *about* — the one named earliest in the prompt.

    image-01 anchors a single subject_reference, so for a two-character beat we
    anchor whoever the prompt mentions first (e.g. "Krishna seated beside Arjuna"
    is a Krishna beat). None if no known character is present.
    """
    text = prompt.lower()
    best: tuple[int, str] | None = None
    for canonical, aliases, _ in _CATALOG:
        positions = [text.find(a) for a in aliases if a in text]
        if positions:
            pos = min(positions)
            if best is None or pos < best[0]:
                best = (pos, canonical)
    return best[1] if best else None


def expand_prompt(prompt: str) -> str:
    """Append canonical descriptions for any detected characters.

    If the prompt mentions "Arjuna" or "Krishna", the matching canonical
    description is appended. Multiple characters = multiple descriptions.
    Each is wrapped in [brackets] so a reader can see what was added.

    Idempotent: characters already expanded in the prompt are not expanded twice.
    """
    detected = detect_characters(prompt)
    if not detected:
        return prompt

    additions = []
    for canonical, _, md_filename in _CATALOG:
        if canonical in detected:
            suffix = _load_suffix(md_filename)
            if suffix and suffix not in prompt:
                additions.append(suffix)

    if not additions:
        return prompt

    return prompt.rstrip() + " " + " ".join(additions)


def reset_cache() -> None:
    """Test helper."""
    _suffix_cache.clear()
    _data_uri_cache.clear()