"""
VaultGuard - Encryption Module
Handles all encryption/decryption using AES-256 (via Fernet) with PBKDF2 key derivation.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


SALT_FILE = os.path.join(os.path.dirname(__file__), "data", "vault.salt")
ITERATIONS = 480_000  # OWASP recommended minimum for PBKDF2-SHA256


def _ensure_data_dir():
    os.makedirs(os.path.dirname(SALT_FILE), exist_ok=True)


def get_or_create_salt() -> bytes:
    """Load existing salt or generate a new one."""
    _ensure_data_dir()
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "rb") as f:
            return f.read()
    salt = os.urandom(32)
    with open(SALT_FILE, "wb") as f:
        f.write(salt)
    return salt


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a 32-byte encryption key from the master password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))


def get_fernet(master_password: str) -> Fernet:
    """Create a Fernet cipher from the master password."""
    salt = get_or_create_salt()
    key = derive_key(master_password, salt)
    return Fernet(key)


def encrypt_text(plaintext: str, master_password: str) -> bytes:
    """Encrypt a plaintext string and return ciphertext bytes."""
    f = get_fernet(master_password)
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_text(ciphertext: bytes, master_password: str) -> str:
    """Decrypt ciphertext bytes and return plaintext string."""
    f = get_fernet(master_password)
    return f.decrypt(ciphertext).decode("utf-8")


def hash_master_password(master_password: str, salt: bytes) -> str:
    """Hash the master password for verification storage (not for encryption key)."""
    combined = master_password.encode("utf-8") + salt
    return hashlib.pbkdf2_hmac("sha256", combined, salt, ITERATIONS).hex()


def verify_master_password(master_password: str, stored_hash: str, salt: bytes) -> bool:
    """Verify a master password against its stored hash."""
    candidate_hash = hash_master_password(master_password, salt)
    return candidate_hash == stored_hash
