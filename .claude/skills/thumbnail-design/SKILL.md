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

The thumbnail is the single biggest lever for click-through. Most viewers in
this niche will see the thumbnail before they read the title, so the visual
must do emotional work on its own.

**Words — the modern pain or promise, never the Sanskrit.**

- Lead with what the viewer is *feeling*, not what the teaching is *called*.
- 2–4 words. Big, legible at phone size. Examples that work:
  - "STOP OVERTHINKING"
  - "INNER PEACE"
  - "END ANXIETY"
  - "LET GO"
  - "ON DUTY"
- Don't put the source on the thumbnail (*"BHAGAVAD GITA"*, *"YOGA SUTRAS"*) —
  save that for the title. The thumbnail earns the click by naming the pain;
  the title earns the impression by naming the source.
- Avoid Sanskrit calligraphy as the headline. It reads devotional and
  undersells the practical promise.

**Image — one emotional visual with a clear focal point.**

- The image should be a **moment the viewer is feeling**, not a setting. A
  stressed face. A calm face at sunrise. A hand on a chest. A chariot wheel.
  A still mind reflected in water.
- High contrast, single focal point. Empty space where the text will sit
  (typically upper or lower third).
- Test it at thumbnail size — if the focal point is unreadable as a 200px
  square, the still is too busy. Pick another.
- **Avoid scripture art on the thumbnail** — no Krishna portraits, no temple
  imagery, no Sanskrit calligraphy as the visual. Those thumbnails look
  devotional and undersell the practical promise. Save the figures for the
  video body, where they earn their place.

## The line not to cross

- Contemplative, not clickbait. No shocked faces, no arrows, no neon, no overpromise.
- Never devotional kitsch (no deity portraits, no temple-poster look).
- The thumbnail must honestly represent the video — don't promise what the script
  doesn't deliver (this also matters for `youtube-policy`).

## Worked pairs (thumbnail + title working together)

These are the shapes our top videos should converge on. The thumbnail earns
the click; the title confirms it.

| Thumbnail | Title |
|---|---|
| Stressed face, hand on chest, "END ANXIETY" | "Stop Anxiety – Bhagavad Gita's Most Ignored Lesson" |
| A still mind reflected in a glass lake | "The 2,000-year-old cure for burnout (Bhagavad Gita)" |
| Thumb hovering over a phone screen | "Why You Can't Stop Scrolling — and what the Yoga Sutras say" |
| Hands letting go of a rope at sunset, "LET GO" | "Let Go – The Yoga Sutras on Attachment" |

Notice the pattern: the **thumbnail names the pain**, the **title names the
source**. Together they cover both halves of the channel promise.

## Mechanics

If the default (first shot + title) isn't right, choose a different base still and pass
a tighter text string. Keep words to 2–4; more than that and nothing reads. The image
is 1280×720 (16:9), the YouTube thumbnail spec.
