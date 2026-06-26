---
name: script-structure
description: Use when writing or editing a Chariot of the Self narration script — the problem→teaching→practice spine, pacing, length, and the script.md format the engine reads (Shot: lines, plain narration).
---

# script-structure

How a Chariot of the Self episode is built. Pair with `brand-bible` for voice.

## The spine (every episode)

The arc below is **time-coded** — pacing is part of the structure. These are
the chunks YouTube's retention graph cares about most.

1. **0:00–0:15 — Hook.** Name the modern problem *and* make a surprising claim.
   Two sentences, no Sanskrit yet. *"You're not anxious because life is
   uncertain. You're anxious because you think you are this small person in the
   story. The Upanishads completely disagree."* If we lose them here, nothing
   else matters. The first `Shot:` (see below) must show the viewer's pain,
   not a landscape.
2. **0:15–1:00 — The turn.** A relatable modern scenario (office, phone at
   night, Sunday dread) followed by a clear promise: *"By the end of this,
   you'll have a 2-minute practice you can use this week."* Name the text or
   figure here — Katha Upanishad, Bhagavad Gita, Patanjali — and translate any
   Sanskrit term once in plain English.
3. **1:00–7:00 — The teaching.** Unpack **one** central idea in plain terms,
   with a story or image from the text. Two or three clear beats, each with its
   own `Shot:` / `Clip:` moment. Use a `Clip:` only for the most dramatic
   moments (Krishna, Arjuna, the chariot, a turning point) — see
   `visual-prompting` skill.
4. **7:00–7:30 — The bridge.** Connect the teaching precisely back to the
   modern problem the viewer named in the hook. Make it concrete: *what does
   this look like in their Tuesday?*
5. **7:30–8:00 — The practice (the payoff).** One specific, doable thing for
   *this week*: when, where, how long. *"Tomorrow morning, before you touch
   your phone, sit 90 seconds and watch your breath."* Not "meditate more" —
   "meditate *this*, *here*, *for this long*." If they can't do it Tuesday,
   rewrite it.
6. **8:00–8:15 — The close + bridge.** A single resonant line (often circles
   back to the chariot), then a soft pointer to a related next video —
   *"If this helped you see your mind differently, watch 'Why You Can't Stop
   Overthinking' next."* The bridge sells the next video and keeps them on the
   channel.

Length: **8–15 minutes total** (~1,300–2,200 spoken words). The pacing above
scales — at 15 min, the teaching stretches to 12 min and the others hold.

## Length & pacing

- 1,300–2,200 spoken words ≈ 8–15 minutes at a slow, contemplative pace.
- Short sentences. One thought per line. Read it aloud — cut anything that trips.
- Introduce a Sanskrit term, translate it once in plain words, then use English.

## File format — `episodes/<slug>/script.md`

- **Plain lines are spoken narration** (the TTS reads them).
- **A line beginning `Shot:`** is an image prompt for that beat (the visual-designer
  adds these; the engine routes them to image generation, not the voiceover).
- The scriptwriter focuses on the words and may leave light `[beat]` markers where
  the image should change. Place a `[beat]` roughly every **8–12 seconds** — if a
  single beat lasts longer, the visual-designer should split it into multiple
  `Shot:` lines (cross-dissolves in the assembly keep the cut smooth). Keep the
  prose final-quality — the owner edits this file directly at GATE 1.

## The hook shot (first 5 seconds)

The very first `Shot:` line in the script is the one most viewers will see
thumbnailed, autoplayed, or scrolled past. Make it **concrete and sensory**, not
abstract or landscape-y.

❌ `"Shot: misty mountains at dawn, muted earth tones"`
   → a wallpaper. Nothing specific is happening. The viewer has no reason to stay.

✅ `"Shot: a phone screen glowing in a dark bedroom, 3:14am on the lock"`
   → a concrete moment, in the viewer's own life, with a time and a place.

The hook shot should **show the problem the viewer is feeling**, not the setting
the teaching will unfold in. Save landscapes and atmosphere for shot 2 onwards;
they work once the viewer is already watching, but they don't pull anyone in.

## Worked example — "Stop Doomscrolling" (8:30 target)

Use this as a reference shape. Replace the topic and figure as needed.

```
[0:00–0:15 — HOOK — ~25 words]
Shot: a thumb scrolling a phone screen in the dark, 3:14am, tired eyes reflected in the glass
You told yourself you'd put the phone down ten minutes ago. Now it's 3am and
your chest is tight and you're still scrolling. Tomorrow you'll feel worse.
[beat]

[0:15–1:00 — TURN — ~95 words, relatable scene + promise]
Shot: a woman at her kitchen table the next morning, phone face-down, staring at coffee
You're not weak. You ran out of a tool two thousand years before it was
designed. The Yoga Sutras of Patanjali — written around the year 200 — have
a name for what your phone does to your attention. They call it *vrittis*,
the whirlpools of the mind.
[beat]
By the end of this, you'll have a two-minute practice that breaks the scroll
loop — and you'll know why the Sutras say this whirlpool isn't the enemy.
[beat]

[1:00–3:30 — TEACHING BEAT 1 — ~280 words, one idea: attention as a muscle]
Shot: a single oil lamp flame in a still room, no flicker
...
[beat]

[3:30–6:30 — TEACHING BEAT 2 — ~340 words, the practice-in-context]
Clip: a charioteer (Arjuna archetype) at rest, reins loose, dawn light on the chariot wheel
...

[6:30–7:30 — BRIDGE — ~120 words, back to the viewer]
Shot: the same dark bedroom as the hook, but the phone is on the nightstand, screen down
...

[7:30–8:00 — PRACTICE — ~90 words, the most concrete part]
Shot: hands on a simple meditation cushion at sunrise, dawn coming through a window
...

[8:00–8:15 — CLOSE + BRIDGE — ~45 words]
Shot: dawn sky over a quiet river, still water reflecting the first light
If this helped you see your mind differently, watch "Why You Can't Stop
Overthinking" next — it goes deeper into the Gita's view of thoughts.
```

Notes on the shape:

- **Word count per chunk is the target.** Scriptwriter can flex ±10%, but if
  the hook is over 40 words you're losing people. If the practice is under
  60 words it's probably too vague.
- **`Shot:` placement** marks visual beats — a new image roughly every 8–12s.
  The cross-dissolve in assembly hides the cut; the change should feel like
  the camera slowly reframing, not a slideshow.
- **`Clip:` is rare.** One per video is plenty. Mark it only for the moment
  where motion adds meaning (the chariot, a deity, a turning-point image).
  Everything else is `Shot:`.
- **The bridge at the end** is the single biggest lever for retention — it
  turns a viewer into a subscriber who watches the next one. Don't end cold.
