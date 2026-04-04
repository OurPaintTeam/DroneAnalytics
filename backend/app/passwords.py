from __future__ import annotations

import base64
import hashlib
import secrets

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


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        iterations = int(iterations_raw)
    except Exception:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    digest = base64.urlsafe_b64encode(derived_key).decode("ascii").rstrip("=")
    return secrets.compare_digest(digest, expected_digest)

