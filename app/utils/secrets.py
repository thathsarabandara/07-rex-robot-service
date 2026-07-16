import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_secret(secret: str) -> str:
    """Hash a secret key using Argon2."""
    return ph.hash(secret)

def verify_secret(secret_hash: str, secret: str) -> bool:
    """Verify a secret against an Argon2 hash."""
    try:
        return ph.verify(secret_hash, secret)
    except VerifyMismatchError:
        return False

def generate_random_secret() -> str:
    """Generate a secure, random string to use as a raw secret."""
    return "rex_sec_" + secrets.token_hex(24)
