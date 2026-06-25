from pathlib import Path
from studio.types import MediaResult


def test_media_result_holds_path_and_usage():
    r = MediaResult(path=Path("/tmp/x.wav"), usage={"characters": 10})
    assert r.path == Path("/tmp/x.wav")
    assert r.usage["characters"] == 10
