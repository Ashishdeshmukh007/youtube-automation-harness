---
name: youtube-seo
description: Use when writing metadata.json for a Chariot of the Self episode — title, description, tags, chapters, category, and visibility for the YouTube upload, in the channel's non-clickbait voice.
---

# youtube-seo

Defines `episodes/<slug>/metadata.json`, which `studio/upload.py` turns into the
YouTube video's snippet + status. Build it in the channel voice — discoverable, never
deceptive.

## metadata.json fields

- **`title`** (≤ ~70 chars) — lead with the **modern problem**, hint at the **source**.
  - Good: "The 2,000-year-old cure for burnout (Bhagavad Gita)"
  - Good: "Why you can't stop scrolling — and what the Yoga Sutras say"
  - Avoid: clickbait that overpromises or disrespects the source.
- **`description`** — structure:
  1. 2–3 line hook restating the problem and the promise.
  2. The practice in one line (the payoff people search for).
  3. **Source attributions** — name the text and verse(s) used.
  4. **Chapters** as `MM:SS Title` lines (YouTube auto-creates chapters from these;
     the first must be `0:00`). Derive from the script beats.
  5. A short, calm sign-off line.
- **`tags`** — the modern problem, its synonyms, the text names (Bhagavad Gita,
  Upanishads, Yoga Sutras, Chanakya), and adjacent searches (meditation, anxiety,
  ancient wisdom). A dozen or so, relevant only.
- **`category_id`** — "22" (People & Blogs) unless a better fit.
- **`visibility`** — **"private"** by default. "public" or `publish_at` (ISO 8601) only
  when the owner has opted in for this episode.

## Voice

Calm and honest, like the script. The description should read like the channel, not
like SEO keyword soup. Earn the click with the title; keep the promise in the video.
