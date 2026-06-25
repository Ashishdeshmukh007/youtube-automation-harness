# Brand Consistency System — Design Spec

**Date:** 2026-06-26
**Channel:** Chariot of the Self
**Trigger:** Owner feedback on the first full render (`2026-06-26-the-gita-on-comparison`):
(1) no intro/outro, (2) no visible captions, (3) characters not consistent / not
recognizable across videos, (4) videos should share one design language.

## Goal

Make every episode look like it came from the same channel: recurring characters
(Arjuna, Krishna) that look the same across videos, one enforced design language,
and standard intro/outro + on-screen captions. Then re-render the current episode
as the first "consistent" video.

## Key findings (from investigation)

- **`subject_reference` works.** MiniMax `image-01` accepts a `subject_reference`
  image and faithfully reproduces the subject's face *and* clothing in new shots.
  This is the real mechanism for cross-video character consistency. It is **not**
  currently wired into `studio/images.py` (the pipeline only appends text).
- **The existing character references are off-brand.** `arjuna.reference.png` /
  `krishna.reference.png` are ornate Rajput-miniature paintings (crown, gold
  jewelry, Sanskrit borders). They contradict the brand's own rules
  (`arjuna.md`: "Never: no crown, no jewelry"; `visual-style.md`: "no devotional
  iconography"). Fed through `subject_reference`, the model dragged a crown onto
  Arjuna. The references must be regenerated before consistency is meaningful.
- **The design language already exists** in `brand/visual-style.md` (palette,
  lighting, camera, hard lines). The gap is *enforcement*: no uniform grade, and
  intro/outro + captions aren't standardized.
- **The engine had two latent bugs** (already fixed this session, with regression
  tests): a `s=hd480` override forcing 480p, and a zoompan-on-looped-image bug
  that made every shot render as shot 0. Lesson baked into this spec: **verify
  rendered frames, not just ffmpeg arg strings.**

## Decisions (owner-approved)

- Sequence: build the system first, then re-render this episode.
- Characters: regenerate clean, on-brand reference sheets (owner approves before lock).

## Scope

**In scope**
- A. Regenerate + lock on-brand character reference sheets (Arjuna, Krishna).
- B. Wire `subject_reference` into `studio/images.py`.
- C. Enforce design language: standard intro/outro template, standard burned-caption
  style, uniform color grade across shots.
- D. Fix intro/outro audio timing in `studio/assemble.py`.
- E. Switch captions to burned-in.
- F. Re-render `2026-06-26-the-gita-on-comparison` through the upgraded pipeline.
- G. Fix the music-loop gap in `studio/pipeline.py` (currently passes the raw ~70s
  track to a 7-minute video).

**Out of scope (noted, deferred)**
- True multi-subject anchoring in a single shot (image-01 anchors one subject).
- New characters beyond Arjuna/Krishna.
- Reworking narration/script content.

## Components

### A. Character reference sheets

- Generate a neutral 3/4 portrait for each character **from the canonical text in
  `brand/characters/<name>.md`** (no crown, no jewelry, correct handwoven cloth,
  brand palette + lighting), at 16:9 or portrait, high quality.
- Owner reviews; on approval, save as `brand/characters/<name>.reference.png`
  (replacing the off-brand paintings) plus a small derived
  `<name>.reference.jpg` (≤768px) used as the API payload.
- The canonical `.md` descriptions stay as-is (they're already on-brand).

### B. `subject_reference` wiring (`studio/images.py` + `providers/minimax.py`)

- `minimax.image_request` gains an optional `subject_reference` param.
- `images.generate`: for each prompt, detect characters (existing
  `characters.detect_characters`). If exactly one is detected, attach that
  character's downscaled reference as `subject_reference`. If two+ are detected,
  attach the **primary** (first detected) and rely on text for the rest; log it.
- A helper loads + caches the ≤768px base64 data URI per character.
- Keep the text suffix expansion too (belt-and-suspenders).

### C. Design-language enforcement

- **Intro/outro template:** keep the existing card style (warm-dark bg, off-white
  title, "Ancient wisdom for the modern mind"). Standardize as the per-episode
  template; the engine always prepends/appends them.
- **Caption style (burn-in):** off-white text `#E0C8A0` on a semi-transparent
  warm-dark band `#3A2620` @ ~70%, bottom third, legible bold, wrapped. Matches
  palette. (Reuses `captions.burn_captions_into_frames`, restyled.)
- **Uniform color grade:** a *subtle* grade applied to the concatenated video in
  assembly (gentle warm push + mild contrast toward the palette), so all shots and
  all episodes share one tone. Subtle by default; owner reviews the rendered result.

### D. Intro/outro audio timing (`studio/assemble.py`)

The card support exists on the video side but the audio side is wrong (voice plays
over the intro; `-shortest` clips the outro). Fix:
- Delay the voiceover by the intro duration (`adelay`) so it starts when shot 0 starts.
- Loop/extend the music to cover intro + shots + outro; gentle fade out on the outro.
- Set the audio chain duration to the full video length (no outro clipping).
- SFX offsets shift by the intro duration (so `phone-ring` lands on the phone shot).
- Add tests that assert the audio is delayed by the intro and that total duration =
  intro + shots + outro. **Plus a frame-level render check in the re-render step.**

### E. Captions burned-in

- Render path uses `captions.transcribe` → `captions.srt` (kept as a sidecar too,
  for YouTube CC) **and** `burn_captions_into_frames` before assembly, restyled per C.

### F. Re-render this episode

- Run the full upgraded pipeline for `2026-06-26-the-gita-on-comparison`.
- **Verify rendered frames:** montage shows 10 distinct shots; characters match the
  locked references; intro/outro present; captions legible; audio synced + no clip.

### G. Music-loop fix (`studio/pipeline.py`)

- Loop the composed music to the voiceover length before assembly, so `/render`
  works for future episodes without manual intervention.

## Testing strategy

- Unit tests for new arg construction (`subject_reference` present; audio `adelay`
  = intro; total duration math).
- **Frame-level verification** for every render (montage of distinct shots; not just
  arg strings) — this is the explicit lesson from the 480p / all-shot-0 bugs.
- Full `pytest` green before and after.

## Known limitations

- image-01 anchors one subject per shot; two-character beats (e.g. Krishna beside
  Arjuna) anchor the focal character only.
- Face drift between episodes is reduced but not zero.
