# Brand Sound FX Library

> Foley + ambient sound effects seeded by the harness. Synthesized on first
> run via ffmpeg (`sine`, `aevalsrc`, `anoisesrc`). Replace any of these with
> a real recorded file of the same name and the engine will pick it up
> automatically — the harness prefers the on-disk file over re-synthesizing.

## Seeded sounds (5 starter, all synthesized from ffmpeg)

| Name | What it sounds like | When the script should use it |
|---|---|---|
| `phone-ring` | Two-tone 440Hz/480Hz repeating, ~1.5s | Whenever a phone rings, pings, or a notification fires |
| `bell` | Decaying 800Hz sine, ~2s | Temple bell, meditation chime, end-of-section marker |
| `wind` | Soft pink-noise wind, ~3s | Outdoor atmosphere, scene-setting, transitions |
| `breath` | Short filtered exhale, ~1s | A moment of pause, a character drawing breath, a beat |
| `silence-gap` | 1s of pure silence | Deliberate pacing gap (rare — use sparingly) |

## How the script invokes them

A line in `script.md`:

```
Sfx: phone-ring
Sfx: bell at 12.5s
```

The first form places the sound at offset 0 within the current shot's section.
The second form places it at an explicit timestamp (seconds from the start of
the video, not from the start of the current shot).

## How to add a new sound

1. Drop a WAV file at `brand/sound-fx/<name>.wav` (mono, 44.1kHz recommended).
2. Use `Sfx: <name>` in any script — no code change needed.
3. The engine reads `brand/sound-fx/<name>.wav` at assembly time and mixes it
   into the audio track at the requested offset.

## How to regenerate the seeds

```bash
.venv/bin/python -c "from studio import sound_fx; sound_fx.seed_sound_fx(force=True)"
```

This rewrites all 5 starter files. Use this if you tweak the synthesizer
specs in `studio/sound_fx.py`.

## Honest limits

- The seeded sounds are **functional placeholders**, not polished foley. They
  communicate "something happened" but don't carry production-quality weight.
- For real production, record or license each sound. The harness doesn't care
  what's in the file — it just reads the path.
- Sfx timing is exact (no fades into voiceover duck). For natural mix, manual
  audio post would be needed; for now we ship clean, deliberate inserts.