# YouTube Automation Harness

> A complete, end-to-end pipeline for running a faceless AI-assisted YouTube channel.
> Three human gates. Everything else automated.

Built for **Chariot of the Self** (ancient Indian wisdom turned into practices for
the modern mind) and templatized so you can fork it for your own niche.

---

## What you get

A working YouTube channel pipeline that:

- **Writes narration scripts** grounded in a chosen wisdom tradition
- **Generates voiceover** with a pinned, consistent narrator voice
- **Produces one still image per narration beat** (every 8–12 s of audio) plus
  optional animated hero clips for the most dramatic moments
- **Mixes audio** — voice + ducked music + sound-fx cues + bookend beds
- **Cross-dissolves** between body shots so the video feels cinematic, not a slideshow
- **Composites bookends** (reusable animated intro/outro)
- **Generates thumbnail + SEO metadata** (title, description, tags, chapter timestamps)
- **Uploads to YouTube** via the Data API v3
- **Enforces three human gates** at the code level — the AI can't accidentally
  publish a video the owner hasn't approved

The engine is provider-agnostic — swap MiniMax for any TTS / image / music API,
swap fal.ai for any image-to-video service, and the pipeline still works.

---

## Architecture

Three layers, each independent:

```
┌─────────────────────────────────────────────────────────────┐
│  Harness layer  (.claude/)                                  │
│  Slash commands · Specialist agents · Skills · Hooks         │
│  The conversational interface for Claude Code                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Engine  (studio/)                                          │
│  Python + ffmpeg                                            │
│  Does the actual media work — TTS, images, music, assembly   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Brand  (brand/)                                            │
│  Your identity: voice, visual style, character refs,         │
│  bookends, sound-fx                                         │
└─────────────────────────────────────────────────────────────┘
```

The engine is the only layer that touches ffmpeg or paid APIs. The harness layer
just calls it.

---

## Quick start (15 min to first render)

### 1. Prerequisites

- macOS or Linux
- Python 3.11
- ffmpeg (`brew install ffmpeg` / `apt install ffmpeg`)
- Whisper (for captions): `pip install openai-whisper`
- API keys for the providers you want to use (see [Costs](#costs))

### 2. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/youtube-automation-harness.git
cd youtube-automation-harness
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

### 3. Configure secrets

```bash
cp .env.template .env
$EDITOR .env   # fill in your keys (see .env.template for the full list)
```

`.env` is gitignored and protected by a `secret-guard` PreToolUse hook. Don't try
to commit it — the hook will refuse.

### 4. Verify credentials

```bash
.venv/bin/python -m studio.verify_credentials
```

Must report **3/3** endpoints reachable. If it doesn't, fix the failing endpoint
before going further.

### 5. Customize your brand

Edit `brand/brand-bible.md` — this is the single source of truth for your
channel's identity. Replace the channel description, voice, visual rules, and
hard lines with your own.

If you have your own intro/outro bookends, drop them in as `brand/intro.mp4` and
`brand/outro.mp4` (1080p, 25 fps, H.264 + AAC).

### 6. Edit `CLAUDE.md`

This is the project guide the AI agent reads at the start of every session. Update
the channel description and any conventions that are specific to you.

### 7. Run

Open this folder in [Claude Code](https://claude.com/code). The slash commands
below drive the full pipeline.

```bash
/propose-topics              # get 5 topic ideas
/new-video <chosen topic>    # draft script  →  GATE 1
/approve-script <slug>       # you approved
/render <slug>               # produces video  →  GATE 2
/approve-video <slug>        # you approved
/publish <slug>              # uploads to YouTube
/channel-status              # see where every episode stands
```

---

## The pipeline (state machine)

Each video is a folder under `episodes/<slug>/` with a `state.json` that tracks
its stage and which gates are approved.

```
proposed
  └─ /new-video        → script_draft
                          └─ /approve-script   → script_approved   [GATE 1]
                                                       └─ /render    → render_review
                                                                         └─ /approve-video → approved [GATE 2]
                                                                                            └─ /publish → published
```

The first "pick a topic" gate (GATE 0) is recorded as the `topic` approval when you
run `/new-video`.

### Why three gates?

You wouldn't trust an AI to write a check, drive your kid to school, or pick what
medication to take — even if it could. Same principle here. Three decisions are
yours alone:

1. **What the video is about** (GATE 0) — you own the channel's direction.
2. **What the video says** (GATE 1) — you own the words.
3. **What the video looks like** (GATE 2) — you own the brand.

Everything else — voice, images, music, editing, captions, SEO, upload — runs
automatically once those three gates are passed.

The engine enforces the gates **at the code level** (`EpisodeState.require`), and
a `PreToolUse` hook double-checks before publish. You literally cannot publish a
video that hasn't been approved.

---

## Slash commands

| Command | Stops at | What it does |
|---|---|---|
| `/propose-topics` | GATE 0 | Research + propose ~5 topics |
| `/new-video <topic>` | GATE 1 | Create episode, draft script |
| `/approve-script <slug>` | — | Record script approval |
| `/render <slug>` | GATE 2 | Voice + images + music + assembly + thumbnail |
| `/approve-video <slug>` | — | Record video approval |
| `/publish <slug>` | done | Finalize SEO + upload to YouTube |
| `/channel-status` | — | Show pipeline state of all episodes |

---

## Specialists (agents)

The harness delegates to a team of specialists. Each owns one part of the craft.

| Agent | Owns |
|---|---|
| `researcher` | Topic ideation, source verification (attribution discipline) |
| `scriptwriter` | Narration scripts in the channel voice |
| `voice-engineer` | Voiceover settings, pacing, consistency |
| `visual-designer` | Shot list (`Shot:` / `Clip:` lines) + thumbnail |
| `video-editor` | Final assembly, pacing review, audio balance |
| `publisher` | SEO metadata + YouTube upload |

The `showrunner` agent orchestrates the whole thing — delegates to specialists,
enforces gates, surfaces costs, and reports failures honestly.

---

## Skills (domain expertise that auto-loads)

| Skill | When it loads |
|---|---|
| `brand-bible` | Before writing or reviewing anything viewer-facing |
| `script-structure` | When writing or editing a script |
| `visual-prompting` | When writing `Shot:` / `Clip:` image prompts |
| `thumbnail-design` | When designing a thumbnail |
| `tts-narration` | When generating the voiceover |
| `ffmpeg-assembly` | When assembling or debugging the final video |
| `indian-wisdom-research` | When sourcing material from the Indian canon (template — replace with your own tradition) |
| `youtube-seo` | When writing `metadata.json` |
| `youtube-policy` | When publishing or designing to stay compliant |

To swap the niche, replace `indian-wisdom-research` with a skill that sources
from your tradition (Stoic philosophers, Biblical commentary, modern psychology
papers, etc.).

---

## Hooks (defense-in-depth guardrails)

Two `PreToolUse` hooks run before every tool call:

- **`secret-guard`** — blocks any tool call that would read or commit `.env`,
  `*.key`, `client_secret*.json`, or `youtube_token.json`.
- **`gate-guard`** — blocks `studio.pipeline render` / `publish` if the episode's
  `state.json` is missing the required prior approval.

The engine also enforces gates in code. If either layer blocks you, that's the
system working — get the approval, don't work around it.

---

## Customizing for your own channel

This is the section most forkers want.

### Step 1 — Your identity: `brand/brand-bible.md`

The brand-bible is a single markdown file. Replace:

- The channel description (one line)
- The "what the channel is NOT" lines (these prevent drift)
- The visual motifs (Himalayan foothills → your equivalents)
- The "hard lines" section (rules that cannot be broken)

### Step 2 — Your voice and settings: `studio/config.py`

```python
@dataclass
class Settings:
    minimax_api_key: str
    minimax_group_id: str
    minimax_voice_id: str       # pin a specific voice for consistency
    fal_key: str = ""           # optional, for hero clip animation
    youtube_client_secret: str  # OAuth client_secret.json path
    youtube_token: str          # OAuth token cache path
```

All settings are loaded from `.env`. The engine never reads from your home dir.

### Step 3 — Your hooks/agents/skills

`.claude/hooks/` — keep `secret-guard` and `gate-guard` (they're channel-agnostic).
Add more if you have specific guardrails.

`.claude/agents/` — adjust the agents' "voice" prompts to match your channel. The
`visual-designer` and `scriptwriter` are the most channel-specific.

`.claude/skills/` — keep the engine skills (`ffmpeg-assembly`, `tts-narration`,
`youtube-seo`, `youtube-policy`). Replace `indian-wisdom-research` with one for
your tradition. Add new skills as needed.

`.claude/commands/` — adjust the order/names if you want. The seven commands
above are the minimum workflow.

### Step 4 — Your bookends (optional but recommended)

A reusable animated intro/outro brand the channel and improve retention.
Generate once with any tool you like (Veo, Runway, Sora) and drop them in:

- `brand/intro.mp4` — 1080p, 25 fps, H.264 + AAC, 3–5 seconds
- `brand/outro.mp4` — same specs, 5–7 seconds
- `brand/bookend-music.wav` — subtle bed to fade under the visuals (optional;
  the engine also adds it via the intro/outro overlay)

The engine concatenates these onto every body video.

### Step 5 — Your episode 1

```bash
/propose-topics
# pick one
/new-video <topic>
# edit script.md
/approve-script <slug>
/render <slug>
# watch the video
/approve-video <slug>
/publish <slug>
```

---

## Costs (per-episode, USD)

These are *recurring* per-episode costs after one-time bookend work is amortized.
Defaults target ~$3–$7 per video.

| Layer | Provider | Per episode |
|---|---|---|
| Voiceover (~2,000 chars) | MiniMax `speech-2.8-hd` | ~$0.10 |
| Images (~70 shots × $0.04) | MiniMax `image-01` | ~$2.80 |
| Music (one bed, ~70s) | MiniMax `music-2.6` | ~$0.50 |
| Hero clips (5 × $0.50 at 480p) | fal.ai Wan 2.2 | ~$2.50 (optional) |
| YouTube upload | YouTube Data API v3 | free |
| **Total without hero clips** | | **~$3.40** |
| **Total with hero clips** | | **~$5.90** |

### Budget guardrails

Two levers keep spend predictable:

- `FAL_MAX_CLIPS_PER_EP` — env var, default `5`. Animates the first N `Clip:`
  beats per episode; the rest auto-demote to Ken-Burns stills.
- `xfade_seconds=0` — opt out of cross-dissolves for hard cuts (saves a tiny
  amount of CPU; mostly useful for A/B comparison).
- `fal.ai` resolution — `studio/providers/fal.py` defaults to `480p` (halved from
  `720p`, assembly upscales to 1080p). Pass `resolution="720p"` to override per-call.

---

## Beyond publishing — research & optimization

The core pipeline produces a video and ships it. Three CLI tools round out the
loop so the next video is smarter than the last one.

### Competitor research

```bash
.venv/bin/python -m studio.competitors \
    --query "ancient indian wisdom anxiety" \
    --max-channels 10 --top-videos 5
```

Discovers the top-view channels in a niche and pulls their top-view videos
into `competitor-reports/competitors-<timestamp>.json`. Use it to find:

- **Underserved topics** — competitors with high views but no coverage of your angle.
- **Title patterns** — what the niche's winning titles look like, so your
  A/B title recommender can be grounded in real data.
- **Channel benchmarks** — typical subscriber counts and views for "doing well"
  in this niche.

Uses the YouTube **Data API v3 server key** (`YOUTUBE_API_KEY` in `.env`,
different from the OAuth used for upload). Public data, no quota concerns.

### A/B title recommender

```bash
.venv/bin/python -m studio.title_recommend episodes/<slug> \
    --niche "ancient indian wisdom anxiety"
```

Reads `metadata.json`, samples the top-view niche titles (via the same Data
API key), then asks the MiniMax chat model for `N` title variants grounded in
the channel voice (see `brand/brand-bible.md` — pain first, scripture second,
proven templates). Writes `episodes/<slug>/title-candidates.json` with each
candidate + the LLM's rationale + which template it maps to.

The owner picks a winner at the title gate and overwrites `metadata.title` before
`/publish`.

### Retention import

```bash
.venv/bin/python -m studio.retention episodes/<slug> --days 30
```

After a video is published, this pulls the **YouTube Analytics** retention
curve (`videoViewRetention` metric) and saves it as
`episodes/<slug>/retention.json` plus a `retention.png` chart. Lets you see:

- **Hook strength** — dropoff in the first 30s.
- **Practice payoff** — where viewers leave relative to the practice beat.
- **Closing bridge** — does the final-15s bridge to next video keep people?

Needs the **OAuth** upload token (same `YOUTUBE_CLIENT_SECRET` /
`YOUTUBE_TOKEN`) plus the YouTube Analytics API enabled for the project.

### Content calendar generator

```bash
.venv/bin/python -m studio.calendar \
    --series "What the Gita knew about ___" \
    --episodes 6 \
    --start 2026-07-06
```

Plans a 6-episode mini-catalogue for a given series scaffold (one of four
canonicals in the brand-bible). The LLM picks topics that:

- fit the series scaffold,
- cover distinct modern problems (no duplicates within the run),
- respect attribution discipline (no invented verses).

Optionally pass `--competitor-report competitor-reports/<file>.json` so the
calendar avoids topics already saturated in the niche.

Writes `content-calendars/calendar-<series>-<start>.json` with `planned_date`,
`slug`, `working_title`, `topic`, `source_text`, and `hook_idea` per entry —
each one ready to feed straight into `/new-video`.

### Vertical short-clip extractor

```bash
.venv/bin/python -m studio.shorts episodes/<slug> --n 2
```

After a video is rendered, this extracts the **N most short-worthy** passages
from `script.md` (chosen by the LLM with the channel's voice + the 45-75s
sweet spot) and renders each one as a vertical 9:16 mp4 with:

- a **burned-in caption** (the LLM's punchy 1-line pick, wrapped to fit
  1080×1920 via Pillow — the sidecar `.srt` approach used for the body
  doesn't work on Shorts/Reels/TikTok),
- the original voiceover segment (loop the music bed quietly underneath
  if `brand/bookend-music.wav` exists).

Writes `episodes/<slug>/shorts/<n>.mp4` plus `shorts.json` with the picked
paragraph indices, time windows, rationale, and caption text — the metadata
to schedule them on YouTube / Reels / TikTok.

---

## Tests

```bash
.venv/bin/pytest
```

221 tests covering: state machine, gate enforcement, hooks, TTS/image/music
adapters, ffmpeg assembly (xfade chain, last-shot extension, color grade,
bookend concatenation), captions, thumbnail, upload, brand assets, configuration
loading, end-to-end pipeline mocking, competitor research, retention import,
the A/B title recommender, the content calendar generator, and the vertical
short-clip extractor.

---

## Project structure

```
.
├── .claude/                      # Harness layer (Claude Code)
│   ├── agents/                   #   specialist roles (6 + showrunner)
│   ├── commands/                 #   slash commands (7)
│   ├── skills/                   #   domain expertise (9)
│   ├── hooks/                    #   PreToolUse guards (2)
│   └── settings.json             #   hook wiring
├── brand/                        # Your channel identity
│   ├── brand-bible.md            #   the single source of truth
│   ├── visual-style.md           #   visual rules
│   ├── characters/               #   character sheets (template)
│   ├── sound-fx/README.md        #   SFX README + placeholder WAVs
│   ├── intro.mp4                 #   YOUR intro bookend (not committed)
│   ├── outro.mp4                 #   YOUR outro bookend (not committed)
│   └── bookend-music.wav         #   YOUR subtle bed (not committed)
├── episodes/<slug>/              # One folder per video
│   ├── topic.md                  #   Problem / Source / Angle / Practice
│   ├── script.md                 #   Narration + Shot:/Clip: lines
│   ├── voiceover.wav             #   Generated
│   ├── shots/00.png ...          #   Generated
│   ├── clips/00.mp4 ...          #   Generated (hero clips)
│   ├── video.mp4                 #   Final rendered video
│   ├── thumb.png                 #   Generated
│   ├── metadata.json             #   SEO metadata
│   └── state.json                #   Stage + approvals
├── studio/                       # The engine (Python + ffmpeg)
│   ├── pipeline.py               #   CLI: render / publish / approve
│   ├── state.py                  #   Stage enum + EpisodeState
│   ├── hooks.py                  #   secret-guard + gate-guard logic
│   ├── config.py                 #   Settings (loaded from .env)
│   ├── tts.py                    #   MiniMax speech-2.8-hd
│   ├── images.py                 #   MiniMax image-01
│   ├── music.py                  #   MiniMax music-2.6
│   ├── captions.py               #   Whisper .srt sidecar
│   ├── assemble.py               #   ffmpeg graph (zoompan + xfade + amix)
│   ├── thumbnail.py              #   Pillow thumbnail composite
│   ├── upload.py                 #   YouTube Data API v3 (OAuth)
│   ├── sound_fx.py               #   SFX event parser + resolver
│   ├── video_clips.py            #   fal.ai image-to-video wrapper
│   ├── pronunciation.py          #   Sanskrit/Hindi phonetic respelling
│   ├── competitors.py            #   CLI: niche/channel research (Data API)
│   ├── retention.py              #   CLI: pull retention curve (Analytics API)
│   ├── title_recommend.py        #   CLI: A/B title variants via LLM
│   ├── calendar.py               #   CLI: 6-episode content calendar
│   ├── shorts.py                 #   CLI: vertical 9:16 short-clip extractor
│   └── providers/                #   Per-API adapters (provider-agnostic)
│       ├── minimax.py
│       ├── fal.py
│       └── youtube_data.py
├── tests/                        # 221 pytest tests
├── .env.template                 # Copy to .env and fill in
├── .gitignore                    # Secrets + generated media
├── CLAUDE.md                     # Project guide the AI reads each session
└── README.md                     # ← you are here
```

---

## Troubleshooting

### `verify_credentials` reports 2/3 or worse

A MiniMax endpoint is down or your key is wrong. The error message names the
endpoint. Re-check `.env`.

### A render fails mid-way

Re-run `studio.pipeline render episodes/<slug>`. The engine is idempotent for
already-generated files (it overwrites them). The state is preserved in
`state.json` and the episode folder.

### The video has wrong shot timing

The engine measures the voiceover duration and divides shots proportionally to
narration. If a beat feels too long or too short, edit `script.md` — move or add
a `Shot:` line where the visual should change.

### YouTube upload is blocked by "App being tested"

Google requires you to add your account as a **test user** under
**APIs & Services → OAuth consent screen → Audience** in Google Cloud Console.
Without this, only the project owner can publish.

### The voice sounds robotic or pronounces Sanskrit wrong

`studio/pronunciation.py` has the channel-specific respelling rules. Edit or
extend them — the TTS reads exactly what's in `script.md`.

### The visuals feel static / slideshow-y

- Confirm you're using the cross-dissolve default (`xfade_seconds=0.5`)
- Confirm the cadence is one new `Shot:` every 8–12 s
- Add more `Clip:` beats for hero moments (capped by `FAL_MAX_CLIPS_PER_EP`)

---

## License

MIT — see [LICENSE](LICENSE).

You can fork, modify, and ship your own channel on top of this. Attribution
appreciated but not required.

The brand assets in `brand/` (intro/outro mp4s, character reference images,
bookend music) are **not** committed — they're the channel-specific identity
that each fork should generate or commission for itself. The markdown templates
(`brand-bible.md`, `characters/*.md`, `visual-style.md`, `sound-fx/README.md`)
are part of the MIT-licensed harness.

---

## Acknowledgments

Built with:

- [MiniMax](https://www.minimax.io) — speech-2.8-hd, image-01, music-2.6 (shared quota on the $20 Token Plan "Plus")
- [fal.ai](https://fal.ai) — Wan 2.2 image-to-video for hero clip animation
- [OpenAI Whisper](https://github.com/openai/whisper) — local caption generation
- [ffmpeg](https://ffmpeg.org) — the actual video assembly
- [YouTube Data API v3](https://developers.google.com/youtube/v3) — publishing
- [Claude Code](https://claude.com/code) — the harness runtime
