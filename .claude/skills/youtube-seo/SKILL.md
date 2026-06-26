---
name: youtube-seo
description: Use when writing metadata.json for a Chariot of the Self episode — title, description, tags, chapters, category, and visibility for the YouTube upload, in the channel's non-clickbait voice.
---

# youtube-seo

Defines `episodes/<slug>/metadata.json`, which `studio/upload.py` turns into the
YouTube video's snippet + status. Build it in the channel voice — discoverable, never
deceptive.

## metadata.json fields

- **`title`** (≤ ~70 chars) — pain first, scripture second. The viewer who
  searched "how to stop overthinking" needs to see that pain in the title
  before any Sanskrit term. The teaching earns the click; the title earns
  the impression.

  **Templates that work in this niche:**

  - `"Stop [X] – [Y]'s most ignored lesson"` — e.g.
    *"Stop Overthinking – Bhagavad Gita's Most Ignored Lesson"*
  - `"The [time period] cure for [modern pain] ([source])"` — e.g.
    *"The 2,000-year-old cure for burnout (Bhagavad Gita)"*
  - `"Why you [symptom] — and what [source] says"` — e.g.
    *"Why you can't stop scrolling — and what the Yoga Sutras say"*

  **Avoid:**

  - Pure Sanskrit titles (*"Dhyana in the Bhagavad Gita"*) — no one searches
    for these.
  - Vague promises (*"The Truth About Peace"*) — too generic to earn a click.
  - Clickbait that disrespects the source (*"This ONE trick from the Gita…"*).
  - Promises the script doesn't keep (matters for `youtube-policy` too).

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

## Series consistency (use the same shape across an arc)

A viewer who watches one video in a series should *want* the next. Use a
repeating title+thumbnail shape across an arc so the channel reads as a
catalog, not a random grab-bag.

- *"What the Gita knew about ____"* — work, anger, duty, results, fear, action
- *"The mind, according to Patanjali"* — attention, distraction, habit
- *"Chanakya on ____"* — enemies, money, discipline, friends
- *"The Self and the witness"* — identity, the observer, ego

The thumbnail of #2 should promise a related teaching, not a topic pivot.
Same words-on-image shape, same emotional focal point, same text size — the
channel's identity is in the repetition.

## Voice

Calm and honest, like the script. The description should read like the channel, not
like SEO keyword soup. Earn the click with the title; keep the promise in the video.
