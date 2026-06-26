# Brand Visual Style — Chariot of the Self

> Appended to **every** image-generation prompt by `studio/visual_style.apply_brand_style()`.
> The visual-designer writes the beat-specific content; this file is the persistent layer.

## Palette (canonical)

These warm cinematic tones anchor scenes and backgrounds. Vivid traditional
colors (Krishna-blue, saffron, gold) are welcome on the figures themselves.

| Role | Hex | RGB | When |
|---|---|---|---|
| Deep shadow | `#202020` | (32, 32, 32) | Night, void, unfocused background |
| Warm shadow | `#3A2620` | (58, 38, 32) | Dusk, indoor, firelight edge |
| Skin shadow | `#604030` | (96, 64, 48) | Flesh in low light, fabric folds |
| Earth mid | `#806040` | (128, 96, 64) | Stone, weathered wood, horse hide |
| Sand | `#A08060` | (160, 128, 96) | Path, sand, open ground |
| Gold highlight | `#C0A070` | (192, 160, 112) | Lamp, dawn, sacred object |
| Sky pale | `#C0BFB0` | (192, 191, 176) | Pre-dawn sky, distant haze |
| Off-white | `#E0C8A0` | (224, 200, 160) | Manuscript, garment edge |

**Forbidden:** pure black `#000000`, pure white `#FFFFFF`, saturated red/blue/green,
neon, jpeg-artifacts, anime cel-shading, calendar-poster gold leaf.

## Lighting rules

- **Default:** soft directional from camera-left at ~30° above horizon. Like dusk sun
  through a high window. Never frontal flat light.
- **Nightscape:** single small warm source (lamp, distant fire, moon through cloud).
  Background must remain readable, not crushed to pure black.
- **Character shots:** key light from camera-left rim, fill from below-right at 20%
  intensity. Subject must be readable in shadow — we don't crush blacks.
- **Always:** visible atmosphere (mist, dust motes, falling light, breath in cold air).
  Flat, particle-free air reads as AI-generated.

## Camera + framing

- Aspect 16:9, output 1280×720 or 1920×1080.
- Default lens: 35mm equivalent (cinematic, not phone-camera).
- Depth of field: shallow (f/2.8 look). Subject/foreground sharp, background soft.
- Composition: rule-of-thirds. Subjects rarely centered. Negative space on the side
  the subject is "looking toward."
- Movement: implies motion but doesn't show motion blur. Frozen instants, not action
  photography.

## Texture + surface

- Weathered surfaces beat polished: cracked leather, salt-stained marble, brushed steel
  with patina, oiled wood with grain showing.
- Skin (when characters appear): warm undertones, visible pores, no airbrushed
  perfection.
- Fabric: hand-woven, undyed cotton, linen, raw silk. No synthetic sheen.

## Traditional iconography (the channel depicts the figures classically)

Deities and epic figures appear in their **classic, recognizable forms** — Krishna
blue-skinned with mukut, peacock feather and flute; Arjuna the crowned warrior-prince
with his bow (Gandiva) — rendered as **living, cinematic film characters**, not flat
poster art. See `brand/characters/*.md` for the canonical look of each.

## What's NEVER allowed (hard lines)

- Every person depicted is **Indian / South Asian** (main figures and incidental
  people alike). Western characters only when a topic specifically calls for one.
- No flat AI-cartoon look (no giant eyes, no anime cel-shading). Render figures as
  living, photoreal cinematic characters.
- No calendar-poster / sweet-shop print look — keep it filmic even when the
  iconography is traditional.
- No neon "om" symbols, no glowing text overlays, no runes.
- No people in modern or Western clothing.

## What this means for the visual-designer

When you write a `Shot:` prompt:

1. State the beat-specific subject + action + setting.
2. Reference character names as plain text ("Arjuna kneeling on a chariot...") —
   `studio.characters` will expand the canonical description.
3. This file's rules get appended automatically — do not duplicate them.

Example final prompt the engine sends to MiniMax:

> "Arjuna the crowned warrior-prince kneeling on a chariot, his great bow across his knees, head bowed, dawn light catching the gold of his crown and armor. Cinematic film still, 35mm lens, shallow depth of field, rich warm color with deep contrast and gold highlights. Soft directional light camera-left at 30°, atmospheric mist, weathered surfaces. Rule of thirds, negative space on the right. Living cinematic character, not flat poster art; no anime, no neon, no modern clothing."