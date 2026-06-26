---
name: ffmpeg-assembly
description: Use when assembling or debugging the final video for a Chariot of the Self episode — what studio/assemble.py does (Ken Burns, music ducking, captions as .srt sidecar), the output spec, and how to read ffmpeg errors.
---

# ffmpeg-assembly

The final cut is built by `studio/assemble.py` (local ffmpeg) inside
`python -m studio.pipeline render`. You invoke the pipeline and judge the result; you
do not reimplement the ffmpeg graph.

## What the engine does

- **Timing** — each still is shown for an equal slice of the voiceover duration
  (measured with `ffprobe`), so the visuals always match the narration length.
- **Motion** — a slow Ken Burns zoom on each still **plus** a 0.5s cross-dissolve
  (`xfade`) between consecutive body shots. The cadence is one new still every
  ~8–12s, so nothing feels static (the cinematic motion School of Life uses).
  Intro/outro cards stay hard-cut against the body so title boundaries read
  cleanly. Set `xfade_seconds=0` to opt out to plain hard cuts.
- **Audio** — music is mixed **very low (0.03)** under the voiceover so words
  stay forward and music never competes.
- **Captions** — produced by Whisper as `captions.srt` and shipped as a **sidecar**
  (uploaded as a YouTube subtitle track), **not burned into the frame**. This keeps the
  visuals clean — the brand has no on-screen text.
- **Output** — `episodes/<slug>/video.mp4`, 1920×1080, H.264 + AAC.

## Judging the cut

- Pacing should feel unhurried; if images change too fast, the script may be too short
  for the shot count, or there are too many `Shot:` lines.
- Voice clear and forward; music present but never competing. If music intrudes, the
  duck level is the lever (in `assemble.py`).

## When it errors

Read the **real ffmpeg/ffprobe error** and fix the cause — a missing input
(`voiceover.wav`, no `shots/*.png`, missing `music.wav`), a zero-length audio, a
corrupt PNG. Never paper over it or fake a success. `video.mp4` is the GATE 2 artifact
the owner watches, so it must genuinely play.
