# Brand Characters Library

> Persistent visual identity for the human figures that recur across Chariot of the
> Self episodes. Each character has a **canonical description** (verbatim — never
> rephrase) and a **reference image** (the face/body the visual-designer should
> prompt toward).

## Why this exists

Modern image-generation models are not natively character-consistent — ask for
"Arjuna" twice and you get two different people. The only practical mitigation
is **prompt repetition with rich, identical description** across every shot that
includes the character. This folder makes that repetition automatic.

## Files

| File | Purpose |
|---|---|
| `arjuna.md` | Canonical Arjuna description + always/never rules + prompt suffix |
| `arjuna.reference.png` | Face anchor — match proportions, hair, skin tone |
| `krishna.md` | Canonical Krishna description + always/never rules + prompt suffix |
| `krishna.reference.png` | Face anchor |
| `README.md` | This file |

## How the harness uses these

`studio.characters.expand_prompt(prompt)` is called by the visual-designer agent
before sending any prompt to MiniMax:

1. Detects character names ("Arjuna", "Krishna") mentioned in the prompt text.
2. For each detected name, appends the **prompt suffix** from the matching `.md`.
3. Returns the expanded prompt.

The agent never rephrases the canonical description. If a beat needs a different
angle on Arjuna, the *action* changes ("kneeling," "standing," "looking away")
but the *description* stays identical.

## Adding a new character

1. Save the reference image as `<name>.reference.png`.
2. Create `<name>.md` following the same structure (Role, Canonical description,
   Always, Never, Reference, Prompt suffix).
3. Add the name to `studio/characters.py`'s detection list.

The character is now available across all future episodes with no other changes.

## How consistency actually works now

`studio.images.generate` conditions each character shot on the locked reference
via MiniMax image-01 **`subject_reference`** (image-conditioned generation) — the
upgrade this folder was always pointing toward. So:

- ✅ Face, hair, beard, and clothing carry across shots and episodes (not just
  the palette) — the reference portrait is fed to the model, not only described.
- ✅ Same compositional rules from each `.md` (Krishna calm/low, Arjuna upright).
- ⚠️ One subject per shot. For a two-character beat (e.g. "Krishna seated beside
  Arjuna") we anchor the figure named **first** in the prompt
  (`characters.primary_character`); the other relies on the text description.
- ⚠️ Minor drift remains (a stray necklace/bead the model adds); the uniform
  color grade in assembly helps tie shots together.

**The reference images must themselves be on-brand.** They are fed verbatim to
the model, so a crowned/ornamented reference produces crowned output. Keep them
plain (no crown, no jewelry beyond what each `.md` allows, no blue Krishna).