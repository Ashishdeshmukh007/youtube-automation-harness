from studio.captions import segments_to_srt, _ts


def test_timestamp_format():
    assert _ts(0) == "00:00:00,000"
    assert _ts(3661.5) == "01:01:01,500"


def test_segments_to_srt():
    segs = [(0.0, 1.5, "First line"), (1.5, 3.0, "Second line")]
    srt = segments_to_srt(segs)
    assert "1\n00:00:00,000 --> 00:00:01,500\nFirst line" in srt
    assert "2\n00:00:01,500 --> 00:00:03,000\nSecond line" in srt
