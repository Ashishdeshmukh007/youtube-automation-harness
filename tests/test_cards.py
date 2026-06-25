from PIL import Image
from studio import cards


def test_intro_card_is_full_hd(tmp_path):
    out = cards.render_intro(tmp_path / "intro.png")
    assert out.exists()
    with Image.open(out) as im:
        assert im.size == (1920, 1080)


def test_outro_card_is_full_hd(tmp_path):
    out = cards.render_outro(tmp_path / "outro.png")
    assert out.exists()
    with Image.open(out) as im:
        assert im.size == (1920, 1080)
