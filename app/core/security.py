import hashlib
import hmac
import os
import secrets
from typing import Tuple

def hash_password(password: str, salt: str = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies a password against the stored salt$hash string."""
    try:
        salt, expected_hash = stored_hash.split('$', 1)
        actual_hash = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False
