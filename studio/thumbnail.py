from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def compose(base_image: Path, title: str, out_path: Path) -> Path:
    img = Image.open(base_image).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img)
    # darken lower third for legibility
    overlay = Image.new("RGB", (W, H // 3), (0, 0, 0))
    img.paste(Image.blend(img.crop((0, H - H // 3, W, H)), overlay, 0.55), (0, H - H // 3))
    font = _font(96)
    text = title.upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, H - H // 3 + 30), text, font=font, fill=(240, 230, 210))
    img.save(out_path)
    return out_path
