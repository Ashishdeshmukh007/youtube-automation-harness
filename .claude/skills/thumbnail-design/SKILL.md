---
name: thumbnail-design
description: Use when designing the thumbnail for a Chariot of the Self episode — choosing the base still, the 2–4 bold words, the contemplative non-clickbait look, and how studio/thumbnail.py composites it.
---

# thumbnail-design

The thumbnail is built by `studio/thumbnail.py` — it composites bold text over a base
still (Pillow) into `episodes/<slug>/thumb.png`. By default the engine uses the first
generated shot as the base and the episode title as the text; your job is to make both
choices deliberate.

## The formula

**One strong contemplative image + 2–4 bold words.**

- **Words** = the modern problem or the promise, in plain English — **not** the Sanskrit.
  "STILL THE MIND", "ON ANGER", "LET IT GO", "STOP SCROLLING". Big, legible at phone size.
- **Image** = the most striking still from the shot list (or generate one purpose-made):
  high contrast, clear focal point, deep shadow, warm light. Empty space where the text
  will sit. Test it tiny — if it's unreadable as a 200px square, pick another.

## The line not to cross

- Contemplative, not clickbait. No shocked faces, no arrows, no neon, no overpromise.
- Never devotional kitsch (no deity portraits, no temple-poster look).
- The thumbnail must honestly represent the video — don't promise what the script
  doesn't deliver (this also matters for `youtube-policy`).

## Mechanics

If the default (first shot + title) isn't right, choose a different base still and pass
a tighter text string. Keep words to 2–4; more than that and nothing reads. The image
is 1280×720 (16:9), the YouTube thumbnail spec.
