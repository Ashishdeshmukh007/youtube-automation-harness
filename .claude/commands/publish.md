---
description: Finalize SEO metadata and upload the approved video to YouTube (default private).
argument-hint: "<episode slug>"
allowed-tools: ["Task", "Read", "Write", "Edit", "Bash"]
---

Publish **$ARGUMENTS**. Requires the video gate — `gate-guard` and the engine both
enforce it; if blocked, the episode is not approved, so stop and get GATE 2.

1. **Finalize metadata.** Delegate to the **publisher** to review/finalize
   `episodes/$ARGUMENTS/metadata.json` (uses `youtube-seo` + `youtube-policy`):
   title, description with source attributions + `MM:SS` chapters, tags, and
   `visibility`. **Keep `visibility: "private"` unless the owner has explicitly opted
   this episode into public** (or set `publish_at` for a scheduled public release).
2. **Policy check.** Confirm original script, varied visuals, original/royalty-free
   music, `selfDeclaredMadeForKids: false` — see `youtube-policy`.
3. **Upload** via the engine:
   ```bash
   .venv/bin/python -m studio.pipeline publish episodes/$ARGUMENTS
   ```
   This reads `metadata.json`, uploads `video.mp4` + `thumb.png`, records
   `youtube_video_id` in `state.json`, and sets stage to `published`. On the first run
   it opens a one-time Google OAuth flow.
4. **Verify and report.** Confirm the returned video ID and report the watch URL and
   its visibility. If the upload fails (auth/quota/API), stop and report the real error —
   never claim a video published when it did not.
