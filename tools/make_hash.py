import base64
import hashlib
import secrets
import sys

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 210_000
PASSWORD_SALT_BYTES = 16


def hash_password(plain_password: str, *, salt: str | None = None, iterations: int = PASSWORD_HASH_ITERATIONS) -> str:
    if salt is None:
        salt = secrets.token_hex(PASSWORD_SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    digest = base64.urlsafe_b64encode(derived_key).decode("ascii").rstrip("=")
    return f"{PASSWORD_HASH_ALGORITHM}${iterations}${salt}${digest}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/make_hash.py <password>")
        raise SystemExit(1)
    print(hash_password(sys.argv[1]), end="")
