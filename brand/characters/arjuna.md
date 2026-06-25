# Arjuna

## Role in the channel
The **seeker** — the human who struggles, doubts, and asks. When a video needs a
figure to embody the modern problem ("the one who can't stop scrolling," "the one
afraid of comparison"), Arjuna is the visual stand-in. He is *you* on the chariot.

## Canonical description (use verbatim in every prompt that includes him)

> "Arjuna, a South Asian man in his early thirties with a lean warrior's build,
> sharp observant eyes, dark close-cropped hair, a thin beard line along the jaw,
> weathered sun-darkened skin. He wears a simple handwoven off-white cotton
> dhoti with a thin rust-colored cloth over one shoulder, leather wrist guards
> darkened with use, no jewelry, no crown, no halo. His expression is the
> signature: alert, slightly furrowed brow, mouth closed but ready to speak."

## Always
- South Asian features. The reference image (`arjuna.reference.png`) is the
  visual anchor — match its face shape, hair, and skin tone across all shots.
- Plain clothing. No royal silks, no gold, no crown.
- A weapon present but not brandished — bow across his knees or on the ground
  beside him. He's a warrior who has stopped fighting.
- Slightly furrowed brow. Always slightly worried. This is the channel's
  signature expression.
- Visible wear on hands and forearms (calluses, scars from bowstring).

## Never
- No crown, no diadem, no royal robes, no jewelry beyond the wrist guards.
- No bow drawn at full tension (we're showing him at rest / in doubt, not in action).
- No blue skin (he's not Krishna), no golden skin.
- No anime stylization, no oversized eyes, no "epic hero" features.
- No smiling unless the script explicitly calls for it.

## Reference
`brand/characters/arjuna.reference.png` — the canonical face. When generating
Arjuna, the visual-designer should include "matching the face and proportions
of the reference image" in the prompt. Consistency comes from the
prompt-anchor approach; the AI model is not natively character-consistent,
but repeating the same description verbatim across episodes makes drift slower.

## Prompt suffix (auto-appended when Arjuna is detected)
```
[Arjuna: lean South Asian warrior in his early thirties, dark close-cropped hair,
thin beard line, off-white dhoti, rust shoulder cloth, leather wrist guards,
no crown, no jewelry, slight furrow of brow, expression of alert concern,
plain period cloth, weathered hands]
```