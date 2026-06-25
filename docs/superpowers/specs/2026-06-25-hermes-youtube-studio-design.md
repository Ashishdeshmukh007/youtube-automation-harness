# Hermes YouTube Studio — Design Spec

**Date:** 2026-06-25
**Status:** Approved design → ready for implementation plan
**Author:** Ashish Deshmukh (with Hermes)

---

## 1. Goal

Build an AI-agent **harness** that runs a faceless YouTube channel end-to-end. The
agent ("Hermes") handles ideation, scripting, voiceover, visuals, assembly,
thumbnail, SEO metadata, and upload. The human (channel owner) interacts at
exactly **three touchpoints**:

1. **Pick a topic** from agent-proposed options.
2. **Approve / edit the script.**
3. **Approve the final rendered video** before it publishes.

Everything else is automated, including the YouTube upload.

The harness is **inspired by the SAW (SAFe Agentic Workflow) template**
(`github.com/Ashishdeshmukh007/Harness-templete`) — it reuses SAW's three-layer
architecture (**Hooks → Commands → Skills**), agent-role pattern, per-unit state
tracking, and gate enforcement — but is purpose-built for content production and
carries none of SAW's software-engineering scaffolding (Stripe, Docker, Linear,
RLS, etc.).

### Channel niche

Stoicism / philosophy "self-mastery" faceless format, in the style of
**@chariotoftheself** (the name nods to Plato's chariot allegory). Calm, deep
narrated voiceover over slow cinematic visuals (statues, nature, abstract
imagery) with ambient music; 8–15 min long-form. In this niche, **voice quality
and script depth are the product**; visuals are slow and secondary.

---

## 2. Scope

### Phase 1 (this spec) — Harness foundation + walking skeleton

- The full harness: agent roles, skills, commands, hooks, brand bible.
- The `studio/` production toolkit (Python + ffmpeg) with provider-agnostic
  adapters, MiniMax wired as the default.
- The episode state machine and three-gate workflow.
- A **walking skeleton**: drive ONE real episode from topic → published
  (as unlisted/private test) end-to-end before enriching anything.

### Phase 2 (future, separate spec) — Enrichment

- AI video clips (MiniMax Hailuo) interleaved with stills.
- Auto-scheduling / cron-driven cadence.
- Analytics feedback loop (titles/thumbnails informed by performance).
- A/B thumbnail testing.
- Richer caption styling / motion graphics.

### Non-goals

- No custom web UI; the interface is the agent + the slash commands + the files.
- No multi-channel / multi-brand support in Phase 1.
- No paid stock-footage integrations in Phase 1.

---

## 3. Architecture

SAW's three-layer model, repurposed:

```
HOOKS      enforce gates & safety        (deterministic, non-skippable)
  ↓
COMMANDS   the workflow steps            (/propose-topics, /new-video, ...)
  ↓
SKILLS     domain expertise, model-loaded (brand-bible, script-structure, ...)
  +
AGENTS     role definitions the showrunner delegates to
  +
STUDIO     deterministic media toolkit   (Python + ffmpeg, called by agents)
```

### 3.1 Agent roles (7)

| Role | Responsibility |
|------|----------------|
| `showrunner` | Orchestrator. Owns the pipeline, delegates to other roles, enforces the three gates, updates episode state. |
| `researcher` | Proposes topics with angles/hooks; gathers source material (stoic canon, accurate attribution). |
| `scriptwriter` | Writes the narration script in channel voice using `brand-bible` + `script-structure`. |
| `voice-engineer` | Generates voiceover via `studio/tts.py` (MiniMax `speech-2.8-hd`); tunes pacing/voice. |
| `visual-designer` | Produces image prompts + shot list (`studio/images.py`, `image-01`); designs the thumbnail. |
| `video-editor` | Assembles final video via `studio/assemble.py` (ffmpeg: Ken Burns, music ducking, crossfades, captions). |
| `publisher` | Finalizes SEO metadata (title/description/tags/chapters) and uploads via `studio/upload.py`. |

### 3.2 Skills (9, model-invoked)

`brand-bible`, `script-structure`, `stoic-research`, `tts-narration`,
`visual-prompting`, `ffmpeg-assembly`, `thumbnail-design`, `youtube-seo`,
`youtube-policy` (reused-content / copyright / monetization compliance).

### 3.3 Commands (7 slash commands)

| Command | Does | Stops at |
|---------|------|----------|
| `/propose-topics` | Researcher proposes ~5 topics+angles. | **Gate 0** (you pick) |
| `/new-video <topic>` | Creates episode, scriptwriter drafts `script.md`. | **Gate 1** (script) |
| `/approve-script` | Records script approval, advances state. | — |
| `/render` | Voice + images + captions + assembly + thumbnail + draft metadata. | **Gate 2** (video) |
| `/approve-video` | Records video approval, advances state. | — |
| `/publish` | Finalizes metadata, uploads to YouTube. | done |
| `/channel-status` | Shows pipeline state of all episodes. | — |

### 3.4 Hooks

- `gate-guard` — refuses `/publish` (and `/render`) unless `state.json` records
  the required prior approval. Gates cannot be skipped by the agent.
- `secret-guard` — blocks committing `.env` / API keys to git.

---

## 4. The episode = unit of work

Each video is a folder under `episodes/`. A `state.json` is the single source of
truth for pipeline stage and gate approvals; hooks enforce against it.

### 4.1 State machine

```
proposed
  → script_draft
      → [GATE 1: human approves/edits script] → script_approved
  → rendering
      → render_review
          → [GATE 2: human approves video] → approved
  → publishing
      → published
```

### 4.2 Episode folder layout

```
episodes/2026-06-25-amor-fati/
├── state.json        # stage + approvals + cost/quota log
├── topic.md          # chosen topic + angle (from Gate 0)
├── script.md         # ← Gate 1 artifact (human edits this directly)
├── voiceover.wav     # MiniMax TTS
├── shots/            # MiniMax image-01 stills + shot list (shots.json)
├── captions.srt      # Whisper word timings
├── music.wav         # MiniMax Music 2.6 ambient track
├── thumb.png         # thumbnail
├── metadata.json     # title / description / tags / chapters / schedule / visibility
└── video.mp4         # ← Gate 2 artifact (human watches this)
```

---

## 5. Production toolkit (`studio/`)

Thin, deterministic, retriable, logged. Agents call these; heavy lifting is code,
not model output. **Provider-agnostic interfaces with MiniMax as the default
adapter** — swapping providers means editing one adapter file, never the harness.

| Script | Purpose | Default impl |
|--------|---------|--------------|
| `tts.py` | text → `voiceover.wav` | MiniMax `speech-2.8-hd` |
| `images.py` | prompts → `shots/*.png` | MiniMax `image-01` |
| `music.py` | brief → `music.wav` | MiniMax `Music 2.6` |
| `captions.py` | audio → `captions.srt` + word timings | Whisper (local) |
| `assemble.py` | audio+images+music+captions → `video.mp4` | ffmpeg (local) |
| `thumbnail.py` | image + text → `thumb.png` | MiniMax image + Pillow overlay |
| `upload.py` | `video.mp4` + metadata → YouTube | YouTube Data API v3 |
| `pipeline.py` | the state machine; reads/writes `state.json` | — |
| `providers/minimax.py` | MiniMax adapter (key, host, endpoints) | — |
| `verify_credentials.py` | **Stage 0**: ping each endpoint, report coverage | — |

### Adapter contract (example, `tts.py`)

```python
def synthesize(text: str, voice_id: str, out_path: Path,
               *, model: str, speed: float, emotion: str | None) -> TtsResult:
    """Provider-agnostic. Default adapter: providers/minimax.py."""
```

---

## 6. Tooling stack (confirmed)

One paid key (MiniMax) covers the media layer; everything else is free/local.

| Stage | Tool | Model / detail | Cost |
|-------|------|----------------|------|
| Voice | MiniMax TTS | `speech-2.8-hd` (HD = video/audiobook narration tier) | Token Plan quota |
| Music | MiniMax Music | `Music 2.6` ambient | Token Plan quota |
| Images | MiniMax Image | `image-01` (~$0.0035/img on PAYG) | Token Plan quota |
| Captions | Whisper | local | free |
| Assembly | ffmpeg | local (Ken Burns, music duck, crossfade, burn captions) | free |
| Upload | YouTube Data API v3 | OAuth to owner's channel | free |
| _(Phase 2)_ Video | MiniMax Hailuo | `Hailuo-2.3` | not in Plus plan |

### 6.1 Billing reality (confirmed from owner's MiniMax dashboard)

Owner is on the **MiniMax Token Plan — Plus ($20/mo)**. The plan page confirms:

- **"Full access to the MiniMax model family (M3 / M2.7 / image / speech / music)."**
- **"Text, image, speech, and music share one quota"** — ~1.7B M3-equivalent
  tokens/month. Ample headroom for several videos/week.
- **Video generation is gated to higher tiers** (Max = 3 clips/day). Phase 1
  uses stills + Ken Burns, so this is not a blocker. Phase 2 AI video would need
  an upgrade or PAYG credits.

Implications for implementation:

- The Token Plan issues a **Subscription Key** distinct from a PAYG API Key, with
  a specific API host. `providers/minimax.py` must use the subscription key and
  correct host; the wrong key type causes auth/billing errors.
- Voice/image/music **share one quota** → `pipeline.py` logs per-episode
  consumption into `state.json` so usage is visible.
- **Stage 0 (`verify_credentials.py`)** validates the subscription key against
  each endpoint (TTS, image, music) before any real run, and reports exactly what
  is covered. This is the first implementation task.

---

## 7. End-to-end flow

1. `/propose-topics` → researcher proposes ~5 topics+angles → **you pick** (Gate 0).
   Episode folder created at `proposed`; chosen topic written to `topic.md`.
2. `/new-video` → scriptwriter drafts `script.md` (brand-bible + script-structure).
   State → `script_draft`. **Stops at Gate 1.**
3. You edit/approve `script.md` → `/approve-script` → state `script_approved`.
4. `/render` → voice → images → music → captions → assembly → thumbnail → draft
   `metadata.json`. State → `render_review`. **Stops at Gate 2.**
5. You watch `video.mp4` → `/approve-video` → state `approved`.
6. `/publish` → publisher finalizes SEO metadata → `upload.py` uploads.
   **Default visibility: private or scheduled** (owner chooses public per episode
   in `metadata.json`). State → `published`.

Cadence in Phase 1 is manual-trigger. Phase 2 may add cron/`/loop` to drive
`/propose-topics` on a schedule, but the three human gates always remain.

---

## 8. Configuration & secrets

```
.env                 # gitignored: MINIMAX_API_KEY (subscription), MINIMAX_HOST,
                     #             MINIMAX_VOICE_ID, YOUTUBE_CLIENT_SECRET, ...
.env.template        # committed template
brand/brand-bible.md # channel identity: themes, voice, do/don't (source of truth)
brand/music/         # (optional) fallback royalty-free tracks
topics/backlog.md    # proposed / approved / used topics
```

- `secret-guard` hook prevents committing `.env`.
- YouTube upload uses OAuth; the refresh token is stored locally (gitignored) so
  uploads run unattended after a one-time auth.

---

## 9. Directory layout (full)

```
Youtube Channel/
├── CLAUDE.md
├── .claude/
│   ├── agents/        # 7 role .md files
│   ├── skills/        # 9 skill dirs
│   ├── commands/      # 7 command .md files
│   ├── hooks/         # gate-guard, secret-guard
│   ├── hooks-config.json
│   └── settings.template.json
├── studio/            # production toolkit (section 5)
│   └── providers/
├── brand/
│   ├── brand-bible.md
│   └── music/
├── topics/
│   └── backlog.md
├── episodes/          # one folder per video (section 4)
├── .env.template
└── docs/superpowers/specs/
```

---

## 10. Verification (walking skeleton)

Phase 1 is "done" when, with a real MiniMax subscription key and YouTube OAuth:

1. `verify_credentials.py` confirms TTS + image + music endpoints respond.
2. A single episode goes topic → published end-to-end.
3. The published video is set to **unlisted/private** (a test, not a public post).
4. All three gates were enforced (cannot publish without recorded approvals —
   verified by attempting `/publish` early and confirming `gate-guard` blocks it).

Visual richness, SEO depth, and cadence automation are explicitly NOT required for
Phase 1 — they are Phase 2.

---

## 11. Risks & open questions

| Risk / question | Mitigation |
|-----------------|------------|
| Subscription key may route differently than PAYG docs assume. | Stage 0 check resolves this empirically before real runs. |
| "Shared quota" could be consumed faster than expected by long TTS. | Per-episode consumption logged in `state.json`; owner has large headroom. |
| YouTube "reused content" / monetization policy for AI faceless channels. | `youtube-policy` skill encodes current rules; scripts must be original, voice human-like, visuals varied. |
| Music copyright / Content ID. | Use MiniMax-generated original music (or `brand/music/` royalty-free fallback). |
| Voice consistency across episodes. | Pin one `MINIMAX_VOICE_ID` in `.env`; brand-bible records it. |
| Whisper/ffmpeg not installed locally. | Implementation plan includes an environment setup/check step. |

---

## 12. Decision log

- **Approach:** Lean SAW-inspired harness (not full SAW adaptation, not bare scripts).
- **Brain:** Hermes/Claude (not MiniMax-M3) writes scripts and orchestrates.
- **Media provider:** MiniMax (default adapter), provider-agnostic interfaces.
- **Music source:** MiniMax-generated (Music 2.6), royalty-free fallback library.
- **Topic selection:** agent proposes, human picks (Gate 0).
- **Publish default:** private/scheduled; owner opts into public per episode.
- **Gates:** three — topic, script, final video.
- **Video (Hailuo):** deferred to Phase 2 (not in the $20 plan).
```
