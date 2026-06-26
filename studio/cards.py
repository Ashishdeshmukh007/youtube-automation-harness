"""Standard intro/outro title cards — the channel's design-language bookends.

Every episode gets the same cards (same palette, type, layout) so the videos read
as one channel. Colors come from brand/visual-style.md.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = (58, 38, 32)        # warm shadow #3A2620
TITLE = (224, 200, 160)  # off-white #E0C8A0
ACCENT = (192, 160, 112)  # gold highlight #C0A070
MUTED = (160, 128, 96)   # sand #A08060


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _centered(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill,
              tracking: int = 0) -> None:
    if tracking:
        # crude letter-spacing for the channel wordmark
        widths = [draw.textlength(ch, font=font) for ch in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = (W - total) / 2
        for ch, w in zip(text, widths):
            draw.text((x, y), ch, font=font, fill=fill)
            x += w + tracking
        return
    w = draw.textlength(text, font=font)
    draw.text(((W - w) / 2, y), text, font=font, fill=fill)


def _divider(draw: ImageDraw.ImageDraw, y: int, half: int = 110) -> None:
    draw.line([(W / 2 - half, y), (W / 2 + half, y)], fill=ACCENT, width=2)


def render_intro(out_path: Path, *, channel: str = "CHARIOT OF THE SELF",
                 tagline: str = "Ancient wisdom for the modern mind") -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _centered(draw, channel, int(H * 0.38), _font(96), TITLE, tracking=8)
    _centered(draw, tagline, int(H * 0.55), _font(44), ACCENT)
    _divider(draw, int(H * 0.64))
    img.save(out_path)
    return out_path


def render_outro(out_path: Path, *, channel: str = "CHARIOT OF THE SELF",
                 cta: str = "Subscribe",
                 tagline: str = "Ancient wisdom for the modern mind") -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _centered(draw, channel, int(H * 0.20), _font(64), ACCENT, tracking=6)
    _centered(draw, cta, int(H * 0.40), _font(108), TITLE)
    _divider(draw, int(H * 0.55))
    _centered(draw, tagline, int(H * 0.64), _font(40), MUTED)
    img.save(out_path)
    return out_path


# --- Transparent text overlays (composited over the animated bookend footage) ---

def _shadowed(draw, text, y, font, fill, *, tracking=0, off=5):
    """Centered text with a soft dark drop shadow so it reads over bright footage."""
    shadow = (10, 8, 6, 220)
    _centered(draw, text, y + off, font, shadow, tracking=tracking)
    _centered(draw, text, y, font, fill, tracking=tracking)


def _bottom_scrim(img: Image.Image, start: float = 0.5, max_alpha: int = 190) -> None:
    """Composite a dark gradient over the lower part of the frame for text legibility."""
    top = int(H * start)
    grad = Image.new("L", (1, H), 0)
    for y in range(top, H):
        grad.putpixel((0, y), int(max_alpha * (y - top) / (H - top)))
    alpha = grad.resize((W, H))
    scrim = Image.new("RGBA", (W, H), (8, 6, 4, 0))
    scrim.putalpha(alpha)
    img.alpha_composite(scrim)


def render_intro_overlay(out_path: Path, *, channel: str = "CHARIOT OF THE SELF",
                         tagline: str = "Ancient wisdom for the modern mind") -> Path:
    # Lower-third title so it never covers the hero subject's face.
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _bottom_scrim(img)
    draw = ImageDraw.Draw(img)
    _shadowed(draw, channel, int(H * 0.72), _font(100), TITLE, tracking=8)
    _divider(draw, int(H * 0.83))
    _shadowed(draw, tagline, int(H * 0.86), _font(44), (240, 224, 190, 255))
    img.save(out_path)
    return out_path


def render_outro_overlay(out_path: Path, *, channel: str = "CHARIOT OF THE SELF",
                         cta: str = "Subscribe",
                         tagline: str = "Ancient wisdom for the modern mind") -> Path:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _bottom_scrim(img, start=0.42, max_alpha=200)
    draw = ImageDraw.Draw(img)
    _shadowed(draw, cta, int(H * 0.60), _font(108), TITLE)
    _divider(draw, int(H * 0.74))
    _shadowed(draw, channel, int(H * 0.79), _font(56), ACCENT, tracking=6)
    _shadowed(draw, tagline, int(H * 0.88), _font(38), (240, 224, 190, 255))
    img.save(out_path)
    return out_path
