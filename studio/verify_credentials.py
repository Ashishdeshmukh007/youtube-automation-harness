import sys
from studio.config import Settings, load_settings
from studio.providers import minimax

_PROBES = {
    "tts": lambda s: minimax.tts_request(s, "test"),
    "image": lambda s: minimax.image_request(s, "a simple grey circle", n=1),
    "music": lambda s: minimax.music_request(s, "soft ambient pad", lyrics=""),
}


def check_endpoint(name: str, s: Settings) -> dict:
    try:
        url, headers, payload = _PROBES[name](s)
        minimax.post_json(url, headers, payload, timeout=60)
        return {"endpoint": name, "ok": True, "error": None}
    except Exception as e:  # noqa: BLE001 - report any failure to the operator
        return {"endpoint": name, "ok": False, "error": str(e)}


def main() -> int:
    s = load_settings()
    failures = 0
    for name in _PROBES:
        r = check_endpoint(name, s)
        mark = "OK " if r["ok"] else "FAIL"
        print(f"[{mark}] {name}" + ("" if r["ok"] else f" -> {r['error']}"))
        failures += 0 if r["ok"] else 1
    print(f"\n{len(_PROBES) - failures}/{len(_PROBES)} endpoints reachable.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
