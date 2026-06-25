---
name: script-structure
description: Use when writing or editing a Chariot of the Self narration script — the problem→teaching→practice spine, pacing, length, and the script.md format the engine reads (Shot: lines, plain narration).
---

# script-structure

How a Chariot of the Self episode is built. Pair with `brand-bible` for voice.

## The spine (every episode)

1. **Hook (0:00–0:30)** — name the modern problem in the viewer's own words. Concrete
   and specific: "You check your phone before you're fully awake. By 9am you're behind."
2. **The turn** — "Centuries ago, someone described this exactly." Name the text/figure.
3. **The teaching** — unpack **one** central idea in plain terms, with a story or image
   from the text. One idea per video, never five.
4. **The bridge** — connect the idea precisely back to the modern problem.
5. **The practice (the payoff)** — one specific, doable thing for *this week*: when,
   where, how long. "Tomorrow morning, before you touch your phone, sit 90 seconds and
   watch your breath" — not "meditate more". If they can't do it Tuesday, rewrite it.
6. **The close** — one resonant line; often circles back to the chariot.

## Length & pacing

- 1,300–2,200 spoken words ≈ 8–15 minutes at a slow, contemplative pace.
- Short sentences. One thought per line. Read it aloud — cut anything that trips.
- Introduce a Sanskrit term, translate it once in plain words, then use English.

## File format — `episodes/<slug>/script.md`

- **Plain lines are spoken narration** (the TTS reads them).
- **A line beginning `Shot:`** is an image prompt for that beat (the visual-designer
  adds these; the engine routes them to image generation, not the voiceover).
- The scriptwriter focuses on the words and may leave light `[beat]` markers where
  the image should change. Keep the prose final-quality — the owner edits this file
  directly at GATE 1.
