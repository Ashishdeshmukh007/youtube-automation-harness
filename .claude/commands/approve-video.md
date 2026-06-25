---
description: Record the owner's final video approval (GATE 2) and advance the episode.
argument-hint: "<episode slug>"
allowed-tools: ["Read", "Bash"]
---

Record **GATE 2**: the owner has watched and approved the final video.

Slug: **$ARGUMENTS**

1. Confirm `episodes/$ARGUMENTS/video.mp4` exists and the episode is at stage
   `render_review`.
2. Record the approval and advance the stage via the engine:
   ```bash
   .venv/bin/python -m studio.pipeline approve episodes/$ARGUMENTS --gate video
   ```
   This writes the `video` approval into `state.json` and sets stage to `approved`.
3. Confirm to the owner: video approved, next step is `/publish $ARGUMENTS`.

Only the owner grants this gate — they must have actually watched the video. Do not
approve on their behalf. Without this approval, both `gate-guard` and the engine will
refuse to publish.
