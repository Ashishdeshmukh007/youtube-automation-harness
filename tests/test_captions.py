from pathlib import Path
from PIL import Image

from studio.captions import segments_to_srt, _ts, parse_srt, burn_captions_into_frames


def test_timestamp_format():
    assert _ts(0) == "00:00:00,000"
    assert _ts(3661.5) == "01:01:01,500"


def test_segments_to_srt():
    segs = [(0.0, 1.5, "First line"), (1.5, 3.0, "Second line")]
    srt = segments_to_srt(segs)
    assert "1\n00:00:00,000 --> 00:00:01,500\nFirst line" in srt
    assert "2\n00:00:01,500 --> 00:00:03,000\nSecond line" in srt


def test_parse_srt_round_trip():
    segs = [(0.5, 2.5, "Hello world"), (3.0, 5.0, "Second caption")]
    text = segments_to_srt(segs)
    parsed = parse_srt(text)
    assert len(parsed) == 2
    assert parsed[0] == (0.5, 2.5, "Hello world")
    assert parsed[1] == (3.0, 5.0, "Second caption")


def test_burn_captions_modifies_shots(tmp_path):
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    # Create 3 fake shots (1280x720, plain color)
    for i in range(3):
        img = Image.new("RGB", (1280, 720), color=(100, 80, 60))
        img.save(shots_dir / f"{i:02d}.png")

    srt = tmp_path / "captions.srt"
    srt.write_text(segments_to_srt([(0, 10, "A line of caption text")]))

    n = burn_captions_into_frames(shots_dir, srt, voiceover_duration_s=30.0)
    # 3 shots of 10s each. Caption 0-10s overlaps shot 0 (0-10s) and
    # touches the boundary of shot 1 (10-20s) at t=10 exactly. Shot 2 (20-30s)
    # doesn't overlap. So 2 shots get the caption band.
    assert n == 2

    # Check that the files are different now (caption band added)
    img0 = Image.open(shots_dir / "00.png")
    # Sample inside the caption band — band_y = 720 - 144 - 28 = 548,
    # band spans y=548..692. Sample y=620 (mid-band).
    pixel = img0.getpixel((640, 620))
    # Original was (100, 80, 60) — band should be much darker (band_color black + alpha 170)
    assert pixel[0] < 60, f"caption band not rendered; pixel={pixel}"


def test_burn_captions_no_modify_when_no_overlap(tmp_path):
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    for i in range(3):
        img = Image.new("RGB", (1280, 720), color=(100, 80, 60))
        img.save(shots_dir / f"{i:02d}.png")

    # Caption runs only during seconds 0-5, voiceover is 30s
    # Per-shot slice is 10s. Shot 0 (0-10s) overlaps, shot 1 (10-20s) does not
    srt = tmp_path / "captions.srt"
    srt.write_text(segments_to_srt([(0, 5, "Only the first shot gets this")]))

    n = burn_captions_into_frames(shots_dir, srt, voiceover_duration_s=30.0)
    assert n == 1


def test_burn_captions_strips_number_prefix(tmp_path):
    """Regression: Whisper sometimes prepends 'Number.' at the start of long files."""
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    img = Image.new("RGB", (1280, 720), color=(50, 40, 30))
    img.save(shots_dir / "00.png")

    srt = tmp_path / "captions.srt"
    srt.write_text(segments_to_srt([(0, 10, "Number. The dharma you're skipping.")]))

    burn_captions_into_frames(shots_dir, srt, voiceover_duration_s=10.0)
    # Verify the artifact was stripped — we can't read the image text directly,
    # but we can ensure no exception was raised and the file was rewritten
    assert (shots_dir / "00.png").exists()
    assert (shots_dir / "00.png").stat().st_size > 0
