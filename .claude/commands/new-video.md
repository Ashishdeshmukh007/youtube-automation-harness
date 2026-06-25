---
description: Create an episode from a chosen topic and draft the script (stops at GATE 1).
argument-hint: "<chosen topic / working title>"
allowed-tools: ["Task", "Read", "Write", "Edit"]
---

The owner has picked a topic (GATE 0). Create the episode and draft its script.

Chosen topic: **$ARGUMENTS**

1. **Make the slug**: `YYYY-MM-DD-kebab-topic` using today's date (e.g.
   `2026-06-25-the-gita-on-burnout`). Create `episodes/<slug>/` and `episodes/<slug>/shots/`.
2. **Write `episodes/<slug>/topic.md`** — first line `# <Working title>`, then the
   Problem / Source (with attribution) / Angle / Practice from the research.
3. **Seed `episodes/<slug>/state.json`** (the topic pick is the GATE 0 approval):
   ```json
   {
     "slug": "<slug>",
     "stage": "proposed",
     "approvals": { "topic": "<today ISO 8601, seconds>" },
     "usage": [],
     "created_at": "<today ISO 8601, seconds>"
   }
   ```
4. **Draft the script**: delegate to the **scriptwriter** agent (uses `brand-bible` +
   `script-structure`). Write clean, final-quality narration to
   `episodes/<slug>/script.md` following the spine (Hook → turn → teaching → bridge →
   **practice** → close), 1,300–2,200 words. Then set `state.json` stage to
   `script_draft` (use `.venv/bin/python -m studio.pipeline approve` is **not** for this —
   just edit the stage field, no approval is granted yet).
5. **Stop at GATE 1.** Tell the owner to read/edit `episodes/<slug>/script.md` and run
   `/approve-script <slug>` when satisfied. Do not render — the script is not approved.
