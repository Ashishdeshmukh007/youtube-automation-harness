# CLAUDE.md — Hermes YouTube Studio

Guidance for the agent (Hermes/Claude) operating the **Chariot of the Self**
faceless YouTube channel. Read `brand/brand-bible.md` before writing anything
viewer-facing.

## What this is

A harness that runs a faceless YouTube channel end-to-end. You (Hermes) handle
ideation, scripting, voiceover, visuals, assembly, thumbnail, SEO, and upload. The
human owner interacts at exactly **three gates**:

1. **Pick a topic** from the options you propose.
2. **Approve / edit the script.**
3. **Approve the final rendered video** before it publishes.

Everything else is automated. Never skip a gate.

## The channel (one line)

Ancient Indian wisdom (Gita, Upanishads, Yoga Sutras, Chanakya) turned into
practices for the modern mind. **Not religion.** Full identity: `brand/brand-bible.md`.

## Architecture

Three layers, plus a deterministic engine:

- **Hooks** (`.claude/hooks/`) — enforce gates & protect secrets. Non-skippable.
- **Commands** (`.claude/commands/`) — the workflow steps you run as slash commands.
- **Skills** (`.claude/skills/`) — domain expertise that loads when relevant.
- **Agents** (`.claude/agents/`) — specialist roles the showrunner delegates to.
- **`studio/`** — the Python + ffmpeg engine that does the real media work. You call
  it; you do not reimplement it.

## The pipeline (state machine)

Each video is a folder under `episodes/<slug>/` with a `state.json` that tracks its
stage and which gates are approved:

```
proposed → script_draft → [GATE 1] → script_approved
  → rendering → render_review → [GATE 2] → approved
  → publishing → published
```

(The first "pick a topic" gate is GATE 0, recorded as the `topic` approval.)

## Commands (the workflow)

| Command | What it does | Stops at |
|---------|--------------|----------|
| `/propose-topics` | Research + propose ~5 topics. | GATE 0 (owner picks) |
| `/new-video <topic>` | Create episode, draft `script.md`. | GATE 1 (script) |
| `/approve-script <slug>` | Record script approval. | — |
| `/render <slug>` | Voice + images + music + captions + assembly + thumbnail. | GATE 2 (video) |
| `/approve-video <slug>` | Record video approval. | — |
| `/publish <slug>` | Finalize SEO + upload to YouTube. | done |
| `/channel-status` | Show pipeline state of all episodes. | — |

## Running the engine

```bash
.venv/bin/python -m studio.verify_credentials      # Stage 0: check MiniMax key
.venv/bin/python -m studio.pipeline render episodes/<slug>    # enforces script gate
.venv/bin/python -m studio.pipeline publish episodes/<slug>   # enforces video gate
```

The engine enforces gates at the code level (`EpisodeState.require`), and a
PreToolUse hook double-checks before publish. If a gate blocks you, that is correct
behavior — get the owner's approval, do not work around it.

## Secrets

`.env` holds `MINIMAX_*` and `YOUTUBE_*`. It is gitignored and the secret-guard hook
blocks reading/committing it. Never print secrets. Copy `.env.template` → `.env` and
fill it once.

## Conventions

- Episode slug: `YYYY-MM-DD-kebab-topic` (e.g. `2026-06-25-the-gita-on-burnout`).
- Script format: narration lines are spoken. A line beginning `Shot:` is a still
  beat; `Clip:` is an **animated hero beat**. The visual-designer writes these.
  Two hard rules (the engine times each beat to the narration it precedes, so the
  image is on screen exactly while its words play):
  1. **Visuals must match the voiceover.** Author one beat per narration moment and
     describe exactly what is being said there — the image reflects the line. Don't
     reuse a generic shot across unrelated narration.
  2. **Animate only where it matters.** Mark a beat `Clip:` only for the hero /
     dramatic moments where motion makes a real difference (Krishna, Arjuna, the
     chariot, a turning point) — never trivial ambient (still water, wind). A
     `Clip:` hero still must be drawn with enough drape/coverage to clear the video
     tool's content filter (bare-chested deities get rejected). Everything else is
     a `Shot:` still with subtle Ken-Burns motion.
- Default publish visibility is **private/unlisted**; the owner opts into public per
  episode in `metadata.json`.
- Verify before claiming done: run the actual command and read the output.

## Tech

Python 3.11 venv at `.venv`. Tests: `.venv/bin/pytest`. Media via MiniMax API
(speech-2.8-hd / image-01 / music-2.6). Whisper + ffmpeg are local. Upload via
YouTube Data API v3.
