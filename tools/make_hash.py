from __future__ import annotations

import sys

import bcrypt


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/make_hash.py <password>")
        raise SystemExit(1)
    print(hash_password(sys.argv[1]))
