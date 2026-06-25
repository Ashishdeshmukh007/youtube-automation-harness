---
description: Research and propose ~5 video topics for the owner to pick (GATE 0).
argument-hint: "[optional theme or problem to focus on]"
allowed-tools: ["Task", "Read", "WebSearch", "WebFetch", "Write"]
---

Propose the next batch of videos. This is **GATE 0** — you propose, the owner picks.

1. Read `brand/brand-bible.md` and `topics/backlog.md`.
2. Delegate to the **researcher** agent (use the `indian-wisdom-research` skill).
   Focus: $ARGUMENTS (if empty, range across the canon and the backlog).
3. Propose **~5 distinct topics**. For each give, in a compact block:
   - **Problem** (in the viewer's words)
   - **Source** (text + specific idea/verse, accurately attributed)
   - **Angle** (the one surprising connection)
   - **Practice** (roughly what they'll walk away able to do)
   - **Working title**
   Avoid topics already in `episodes/` (recently used) or marked Used in the backlog.
4. **Stop and present the options.** Do not create an episode yet.

The owner picks one (GATE 0). When they do, they run `/new-video <chosen topic>` —
which creates the episode folder. Add any strong un-picked ideas to the **Proposed**
section of `topics/backlog.md` so they aren't lost.
