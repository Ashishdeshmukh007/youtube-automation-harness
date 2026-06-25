# Handoff — Hermes YouTube Studio (Chariot of the Self)

Paste the prompt below into Claude Code CLI, run from the project root:
`cd "/Users/ashishdeshmukh/projects/Youtube Channel" && claude`

---

## Handoff prompt

We're building **Hermes YouTube Studio**: an AI-agent harness that runs the faceless
YouTube channel **"Chariot of the Self"** end-to-end, with three human gates (pick
topic → approve/edit script → approve final video). Continue the in-progress work.

**Read these first:** `CLAUDE.md`, `brand/brand-bible.md`, the spec
`docs/superpowers/specs/2026-06-25-hermes-youtube-studio-design.md`, and the Plan 2
context below. The channel is **ancient Indian wisdom (Gita / Upanishads / Yoga
Sutras / Chanakya) for the modern mind — NOT stoicism, NOT religion.**

### What's already done
- **Plan 1 — `studio/` engine: COMPLETE and merged to `main`.** Python package with
  config, gate-enforcing state machine, MiniMax adapters (tts/image/music), Stage-0
  credential check, Whisper captions, ffmpeg assembly (Ken Burns + music duck;
  captions are an `.srt` sidecar, not burned in), thumbnail, YouTube upload, and a
  `pipeline` CLI. **28 tests pass** (`.venv/bin/pytest`). Plan: `docs/superpowers/plans/2026-06-25-studio-toolkit.md`.
- **Plan 2 — harness layer: IN PROGRESS** on branch **`feat/harness-layer`**.
  Done: `CLAUDE.md`, `brand/brand-bible.md`, 6 of 7 agents
  (`showrunner, researcher, scriptwriter, voice-engineer, visual-designer,
  video-editor`), and empty skill directories under `.claude/skills/`.

### What's left to build (Plan 2)
1. **`.claude/agents/publisher.md`** — final agent (SEO metadata + YouTube upload;
   default visibility private/unlisted; tools: Read, Write, Edit, Bash).
2. **9 skill bodies** — write `SKILL.md` (with `name`/`description` frontmatter) in
   each existing `.claude/skills/<name>/`: `brand-bible`, `script-structure`
   (problem→teaching→practice spine), `indian-wisdom-research` (Gita/Upanishads/Yoga
   Sutras/Chanakya, accurate attribution, "not religion"), `tts-narration`,
   `visual-prompting`, `ffmpeg-assembly`, `thumbnail-design`, `youtube-seo`,
   `youtube-policy` (reused-content/copyright/monetization).
3. **7 commands** in `.claude/commands/`: `propose-topics`, `new-video`,
   `approve-script`, `render`, `approve-video`, `publish`, `channel-status`. Each
   should drive the `studio/` engine and the state machine. `render` runs
   `.venv/bin/python -m studio.pipeline render episodes/<slug>`; `publish` runs the
   publish subcommand; `approve-script`/`approve-video` set the gate in `state.json`.
4. **2 hooks** in `.claude/hooks/`: `secret-guard` (block reading/committing `.env`)
   and `gate-guard` (PreToolUse: block a `pipeline publish` when `state.json` lacks
   the `video` approval). Wire them in a `.claude/settings.template.json`. Test the
   hook scripts.
5. **`topics/backlog.md`** seed (a starter idea bank — see brand-bible series ideas).
6. Then **commit, merge `feat/harness-layer` to `main`**, confirm `.venv/bin/pytest`
   still green.

### After Plan 2 — live smoke test (Task 14 in the studio plan)
Needs the owner's credentials in `.env` (copy from `.env.template`):
- MiniMax **subscription** key + `MINIMAX_GROUP_ID` + `MINIMAX_HOST` + a chosen
  `MINIMAX_VOICE_ID` (owner is on the $20 MiniMax Token Plan "Plus" — covers
  image/speech/music under one shared quota; video/Hailuo is Phase 2).
- YouTube `client_secret.json` (Google Cloud OAuth desktop app, YouTube Data API v3).

Then: `.venv/bin/python -m studio.verify_credentials` must show 3/3 endpoints OK
before any real render. **Do not proceed past a failing Stage 0** — the MiniMax
payload fields in `studio/providers/minimax.py` may need tuning against the live API
(TTS/music return hex audio in `data.audio`; image returns `data.image_urls`).
Then render + publish one test episode as **unlisted**.

### Working agreements
- Use the superpowers skills (brainstorming→writing-plans→executing-plans) as
  established. Follow TDD for any new Python. Frequent commits.
- Never skip a gate; the gates are the product's safety. Verify before claiming done
  (run the real command, read the output).
- Don't print secrets. `.env` is gitignored.

Start by reading `CLAUDE.md` and the spec, then finish Plan 2 beginning with the
`publisher` agent and the skill bodies.
