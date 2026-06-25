---
name: visual-prompting
description: Use when writing Shot: image prompts for a Chariot of the Self episode — the contemplative non-devotional aesthetic, prompt anatomy, shot cadence, and how the engine turns Shot: lines into stills.
---

# visual-prompting

You write the `Shot:` lines in `script.md`. The engine (`studio/images.py`, MiniMax
`image-01`) generates one still per `Shot:` line during render; `assemble.py` gives
each a slow Ken Burns move.

## The aesthetic (from the brand-bible)

- Slow, cinematic, contemplative. Visuals breathe; nothing busy or fast.
- Palette: muted earth tones, warm low light, deep shadow, dawn/dusk gold.
- Motifs: Himalayan foothills and rivers, weathered palm-leaf manuscripts, a lone
  chariot or horse at distance, oil lamps, still water, hands, old stone, banyan
  trees, the night sky.
- **Tasteful and modern — never devotional kitsch.** No deity portraits, no temple-
  poster look, no neon "om", no AI-cartoon gods. If it looks like a sweet-shop
  calendar, rewrite the prompt.

## Prompt anatomy

`subject + setting + light + mood + constraints`, e.g.:

> Shot: a weathered palm-leaf manuscript on dark stone, a single oil lamp just out of
> frame, warm low light, deep shadow, dust motes, contemplative and still, cinematic,
> 16:9, no text, no people

- Always include **"no text, no people"** (unless a distant silhouette is intended)
  and **16:9**. On-frame text is forbidden — captions ship as a separate track.
- Vary subjects across the episode so YouTube doesn't read it as "reused content".

## Cadence

One image every ~15–25 seconds of narration. For an 8–15 min video that's roughly
20–45 shots. Place a new `Shot:` where the idea or emotional beat turns, not on a fixed
clock. The first shot doubles as the thumbnail base, so make it strong.
