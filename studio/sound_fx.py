"""Sound design — `Sfx:` lines in script.md are parsed here, and the corresponding
audio files are seeded from ffmpeg's synthesizers so the engine has something to
mix even without recorded foley.

Script syntax (additive, doesn't break existing scripts):

    Sfx: phone-ring         <- plain name (uses default offset = 0)
    Sfx: bell at 2.5s       <- explicit offset (seconds from start)

Parsed results:
    events = [{"name": "phone-ring", "offset_s": 0.0}, ...]

Synthesis (idempotent):
    seed(brand/sound-fx/)  -- writes phone-ring.wav, bell.wav, etc. using
    ffmpeg's sine + aevalsrc filters. Safe to call repeatedly; existing files
    are not overwritten.
"""
import re
import subprocess
from pathlib import Path

# Default sound-fx directory; reads + writes wav files here.
SOUND_FX_DIR = Path(__file__).resolve().parents[1] / "brand" / "sound-fx"

# Each entry: (name, ffmpeg_args_list). The ffmpeg call synthesizes a mono
# 44.1kHz WAV of ~2 seconds. Replace these with real recorded files when you have them.
_SEED_SPECS: list[tuple[str, list[str]]] = [
    # phone-ring: classic two-tone 440Hz + 480Hz, repeating, ~1.5s
    (
        "phone-ring",
        [
            "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4:sample_rate=44100",
            "-f", "lavfi", "-i", "sine=frequency=480:duration=0.4:sample_rate=44100",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4:sample_rate=44100",
            "-filter_complex",
            "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a];[a]afade=t=out:st=1.0:d=0.5[a]",
            "-map", "[a]", "-ac", "1", "-ar", "44100",
        ],
    ),
    # bell: temple-bell-like decaying sine at 800Hz
    (
        "bell",
        [
            "-f", "lavfi", "-i",
            "sine=frequency=800:duration=2.0:sample_rate=44100",
            "-af", "afade=t=out:st=0:d=2.0,volume=0.8",
            "-ac", "1", "-ar", "44100",
        ],
    ),
    # wind: low-passed pink noise for soft wind
    (
        "wind",
        [
            "-f", "lavfi", "-i",
            "anoisesrc=duration=3.0:color=pink:amplitude=0.15:sample_rate=44100",
            "-af", "lowpass=f=400,afade=t=in:st=0:d=0.5,afade=t=out:st=2.5:d=0.5",
            "-ac", "1", "-ar", "44100",
        ],
    ),
    # breath: short exhale, filtered noise burst
    (
        "breath",
        [
            "-f", "lavfi", "-i",
            "anoisesrc=duration=1.0:color=brown:amplitude=0.4:sample_rate=44100",
            "-af", "highpass=f=200,lowpass=f=1500,afade=t=in:st=0:d=0.1,afade=t=out:st=0.5:d=0.5",
            "-ac", "1", "-ar", "44100",
        ],
    ),
    # silence-gap: 1s of pure silence as a pacing tool
    (
        "silence-gap",
        [
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "1.0", "-ac", "1", "-ar", "44100",
        ],
    ),
]


# Parse "Sfx: name" or "Sfx: name at 2.5s"
_SFX_LINE_RE = re.compile(
    r"^\s*[Ss][Ff][Xx]\s*:\s*([a-zA-Z0-9_\-]+)(?:\s+at\s+([\d.]+)s?)?\s*$"
)


def parse_script(script_text: str) -> list[dict]:
    """Return a list of {name, offset_s} events parsed from `Sfx:` lines."""
    events = []
    for line in script_text.splitlines():
        m = _SFX_LINE_RE.match(line)
        if m:
            events.append({
                "name": m.group(1),
                "offset_s": float(m.group(2)) if m.group(2) else 0.0,
            })
    return events


def seed_sound_fx(force: bool = False) -> list[Path]:
    """Synthesize the seeded sound-fx library. Idempotent unless force=True.

    Returns the list of paths actually written.
    """
    SOUND_FX_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name, args in _SEED_SPECS:
        out = SOUND_FX_DIR / f"{name}.wav"
        if out.exists() and not force:
            continue
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args + [str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and out.exists():
            written.append(out)
        else:
            raise RuntimeError(
                f"Failed to synthesize {name}.wav: {r.stderr[-200:]}"
            )
    return written


def resolve_event(event: dict) -> Path | None:
    """Return the wav path for a parsed Sfx event, or None if unknown."""
    path = SOUND_FX_DIR / f"{event['name']}.wav"
    return path if path.exists() else None


def list_available() -> list[str]:
    """Names of seeded sound-fx files present on disk."""
    if not SOUND_FX_DIR.exists():
        return []
    return sorted(p.stem for p in SOUND_FX_DIR.glob("*.wav"))