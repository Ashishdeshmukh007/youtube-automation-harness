from pathlib import Path
from PIL import Image
from studio.thumbnail import compose


def test_compose_produces_1280x720(tmp_path):
    base = tmp_path / "base.png"
    Image.new("RGB", (1920, 1080), (20, 20, 30)).save(base)
    out = tmp_path / "thumb.png"
    compose(base, "AMOR FATI", out)
    img = Image.open(out)
    assert img.size == (1280, 720)
