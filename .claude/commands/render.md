---
description: Render the full video (voice, images, music, captions, assembly, thumbnail) — stops at GATE 2.
argument-hint: "<episode slug>"
allowed-tools: ["Task", "Read", "Write", "Edit", "Bash"]
---

Produce the video for **$ARGUMENTS**. Requires the script gate (the engine enforces it).

1. **Stage 0 — credentials.** If you have not this session, confirm MiniMax is reachable:
   ```bash
   .venv/bin/python -m studio.verify_credentials
   ```
   It must report **3/3** endpoints. If not, stop and report — do not render against a
   failing Stage 0.
2. **Shot list.** Delegate to the **visual-designer** to add `Shot:` lines to
   `episodes/$ARGUMENTS/script.md` (one image every ~15–25s of narration) if they
   aren't already there. Uses `visual-prompting`.
3. **Render** via the engine (voice → images → music → captions → assembly → thumbnail):
   ```bash
   .venv/bin/python -m studio.pipeline render episodes/$ARGUMENTS
   ```
   This blocks unless `state.json` has the `script` approval, advances stage to
   `render_review`, and logs MiniMax usage. If it errors, read the real error and fix
   the cause (see `ffmpeg-assembly` / `tts-narration`). Never fake success.
4. **Draft metadata.** Have the **publisher** write `episodes/$ARGUMENTS/metadata.json`
   (title / description / tags / chapters / `visibility: "private"`) using `youtube-seo`.
   This is a draft for the owner to review; it is not uploaded yet.
5. **Stop at GATE 2.** Tell the owner to watch `episodes/$ARGUMENTS/video.mp4` (and check
   `thumb.png`) and run `/approve-video $ARGUMENTS` when satisfied. Surface MiniMax usage
   from `state.json`.
