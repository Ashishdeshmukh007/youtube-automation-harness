"""Sanskrit pronunciation layer for TTS.

MiniMax speech-2.8-hd mangles Sanskrit terms when fed the usual English
transliteration ("Gita", "dharma", "Arjuna"). We respell them phonetically so an
English-trained voice lands much closer to the real pronunciation.

This is a best-effort, hand-tuned map — adjust entries when a word still sounds
off. Keys are matched whole-word and case-insensitively; a leading capital in the
source (e.g. a name at the start of a sentence) is preserved.
"""
import re

# term (lowercase) -> phonetic respelling for an English TTS voice.
# Order-independent; matching is longest-first so plurals win over singulars.
# Keep respellings smooth and hyphen-free — hyphens/CAPS make the voice pause or
# spell letters out, which is worse than the original.
_RESPELL: dict[str, str] = {
    "dharma": "dhurma",
    "dharmas": "dhurmas",
    "adharma": "uhdhurma",
    "arjuna": "Arjun",
    "gita": "Geeta",
    "bhagavad": "Bhuhguvad",
    "upanishad": "Oopanishad",
    "upanishads": "Oopanishads",
    "mahabharata": "Mahabharat",
    "kurukshetra": "Kurukshaytra",
    "chanakya": "Chaanakya",
}

# Longest keys first so "upanishads"/"dharmas" match before their singulars.
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_RESPELL, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _sub(m: re.Match) -> str:
    original = m.group(0)
    respelled = _RESPELL[original.lower()]
    if original[:1].isupper():
        respelled = respelled[:1].upper() + respelled[1:]
    return respelled


def apply(text: str) -> str:
    """Respell known Sanskrit terms in `text` for clearer TTS pronunciation."""
    return _PATTERN.sub(_sub, text)
