---
name: youtube-policy
description: Use when publishing a Chariot of the Self video or designing the pipeline to stay compliant — YouTube's reused-content / repetitious-content rules, copyright (music, images, text), monetization, and made-for-kids settings for an AI-assisted faceless channel.
---

# youtube-policy

What keeps an AI-assisted faceless channel clear of strikes and eligible for
monetization. Apply at publish, and design earlier stages to satisfy it.

## Reused / repetitious content (the main risk)

YouTube demonetizes channels that mass-produce templated, low-effort, or duplicated
videos. Defend with **genuine originality every episode**:

- **Original script** — written for this video, never scraped or spun from another's.
- **Human-like, varied narration** — one consistent real-sounding voice, not robotic
  TTS that reads identically every time.
- **Varied visuals** — fresh image prompts per episode (see `visual-prompting`); don't
  reuse the same stills across videos.
- **Commentary/transformation** — the channel's value is the *teaching and the
  practice*, not raw text. That transformation is what makes it original.

## Copyright

- **Music** — use MiniMax-generated original tracks (or the `brand/music/` royalty-free
  fallback). Never copyrighted music; it triggers Content ID and kills monetization.
- **Images** — AI-generated stills are original. Don't prompt for living artists' styles
  or recognizable copyrighted/brand imagery.
- **Quotes** — short attributed verses from ancient (public-domain) texts are fine;
  attribute them. Don't reproduce a modern translator's copyrighted translation verbatim.

## Other settings

- **Made for kids** — set **false** (`selfDeclaredMadeForKids: false`, already in
  `upload.py`); this is adult-oriented contemplative content.
- **No medical/clinical claims** — practices are reflective, not therapy. Don't promise
  to cure conditions.
- **Default visibility private/unlisted** — public is an explicit per-episode choice.

## At publish

Sanity-check the episode against the above before `/publish`. If anything looks like it
could read as reused/templated or copyright-risky, fix it rather than shipping and
hoping.
