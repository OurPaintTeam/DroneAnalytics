# tools/make_user_hash.py
import sys
import bcrypt
from app.config import PASSWORD_SALT

def _password_bytes(password: str) -> bytes:
    return (password + PASSWORD_SALT).encode("utf-8")

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(_password_bytes(plain_password), bcrypt.gensalt()).decode()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_user_hash.py <password>")
        sys.exit(1)
    pw = sys.argv[1]
    print(hash_password(pw))