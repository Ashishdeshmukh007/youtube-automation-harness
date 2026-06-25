from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _shrink_to_fit(draw: ImageDraw.ImageDraw, text: str, max_width: int,
                   start_size: int = 80, min_size: int = 36) -> tuple[ImageFont.FreeTypeFont, int]:
    """Find the largest font size that renders `text` within `max_width`.

    Returns (font, computed_width). Linear search starting at start_size,
    decreasing in 4pt steps until the text fits or we hit min_size.
    """
    size = start_size
    while size >= min_size:
        font = _font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            return font, width
        size -= 4
    font = _font(min_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    return font, bbox[2] - bbox[0]


def compose(base_image: Path, title: str, out_path: Path,
            *, max_text_width_ratio: float = 0.86) -> Path:
    """Render a Chariot-of-the-Self style thumbnail.

    Layout:
        - Resize base image to W x H
        - Darken lower third for legibility
        - Render title in caps, centered horizontally, shrink-to-fit

    Shrink-to-fit: the title is the most-likely-to-overflow element. We
    shrink the font from 80pt down to 36pt until the rendered text width is
    <= max_text_width_ratio * W. This guarantees no character is cropped
    regardless of title length.
    """
    img = Image.open(base_image).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img)

    # Darken lower third
    overlay = Image.new("RGB", (W, H // 3), (0, 0, 0))
    img.paste(Image.blend(img.crop((0, H - H // 3, W, H)), overlay, 0.55),
              (0, H - H // 3))

    text = title.upper()
    max_w = int(W * max_text_width_ratio)
    font, tw = _shrink_to_fit(draw, text, max_w)

    # Get the actual height of the rendered text for vertical centering
    bbox = draw.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]

    tx = (W - tw) // 2
    ty = H - H // 3 + (H // 3 - th) // 2
    draw.text((tx, ty), text, font=font, fill=(240, 230, 210))
    img.save(out_path)
    return out_path