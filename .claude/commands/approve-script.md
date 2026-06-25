---
description: Record the owner's script approval (GATE 1) and advance the episode.
argument-hint: "<episode slug>"
allowed-tools: ["Read", "Bash"]
---

Record **GATE 1**: the owner has approved (and possibly edited) the script.

Slug: **$ARGUMENTS**

1. Confirm `episodes/$ARGUMENTS/script.md` exists and the episode is at stage
   `script_draft`. If the owner edited it, that's expected — the file on disk is the
   approved version.
2. Record the approval and advance the stage via the engine:
   ```bash
   .venv/bin/python -m studio.pipeline approve episodes/$ARGUMENTS --gate script
   ```
   This writes the `script` approval into `state.json` and sets stage to
   `script_approved`.
3. Confirm to the owner: script approved, next step is `/render $ARGUMENTS`.

Only the owner grants this gate. Do not approve a script on their behalf.
