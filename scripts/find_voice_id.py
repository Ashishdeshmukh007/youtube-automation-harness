#!/usr/bin/env python3
"""List available MiniMax voice IDs using only Python stdlib.

Reads API key + host from .env, tries a few common endpoints and request shapes,
and prints whatever JSON the API returns. No external packages needed.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def post(url: str, headers: dict, body: dict, timeout: int = 30) -> tuple[int, str]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return 0, f"URL error: {e}"


def main() -> int:
    env_path = Path(".env")
    if not env_path.exists():
        print("ERROR: .env not found in current directory.")
        return 2

    env = load_env(env_path)
    api_key = env.get("MINIMAX_API_KEY", "")
    host = env.get("MINIMAX_HOST", "https://api.minimax.io")

    if not api_key or api_key.startswith("***") or len(api_key) < 20:
        print("ERROR: MINIMAX_API_KEY in .env looks empty or invalid.")
        print(f"  (length: {len(api_key)})")
        return 2

    print(f"Host: {host}")
    print(f"API key length: {len(api_key)}")
    print()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Try several endpoint + payload combinations. The right combo is unknown
    # without docs, so we cast a wide net and report everything that comes back.
    attempts = [
        ("/v1/get_voice", {}),
        ("/v1/get_voice", {"voice_type": "system"}),
        ("/v1/get_voice", {"type": "system"}),
        ("/v1/voice/list", {}),
        ("/v1/voices", {}),
        ("/v1/t2a_v2/voices", {}),
        ("/v1/tts/voices", {}),
    ]

    for path, payload in attempts:
        url = f"{host}{path}"
        print(f"=== POST {url}  body={payload} ===")
        status, body = post(url, headers, payload)
        print(f"HTTP {status}")
        # Try to pretty-print JSON; otherwise show as-is.
        try:
            parsed = json.loads(body)
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            # Truncate huge responses to keep terminal readable.
            if len(pretty) > 2000:
                print(pretty[:2000] + "\n... (truncated)")
            else:
                print(pretty)
        except json.JSONDecodeError:
            print(body[:500])
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())