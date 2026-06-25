---
description: Show the pipeline state of every episode.
allowed-tools: ["Read", "Bash"]
---

Show where every episode stands in the pipeline.

1. List `episodes/*/state.json`.
2. For each, read `slug`, `stage`, which `approvals` are recorded (topic / script /
   video), and `youtube_video_id` if present.
3. Render a compact table sorted by slug, e.g.:

   | Episode | Stage | Gates (topic/script/video) | YouTube |
   |---------|-------|----------------------------|---------|
   | 2026-06-25-the-gita-on-burnout | render_review | ✓ / ✓ / — | — |

4. If there's MiniMax usage logged, note total characters/images/music per episode so
   the owner can see shared-quota consumption.
5. Suggest the natural next command for any in-flight episode (e.g. "→ `/approve-video
   <slug>`" for one at `render_review`).

Read-only. This command never changes state.
