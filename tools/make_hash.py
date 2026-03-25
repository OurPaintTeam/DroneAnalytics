from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.passwords import hash_password


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/make_hash.py <password>")
        raise SystemExit(1)
    print(hash_password(sys.argv[1]), end="")
