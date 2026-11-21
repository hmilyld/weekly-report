import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PBKDF2_ITERATIONS = 100_000
SALT_SIZE = 32
KEY_SIZE = 32
NONCE_SIZE = 12


def generate_salt() -> bytes:
    return os.urandom(SALT_SIZE)


def derive_key(password: str, salt: bytes) -> bytes:
    # LEGACY KDF — used ONLY to decrypt pre-envelope data during migration.
    # Parameters are FROZEN: changing iterations/hash/salt handling derives a
    # different key and makes existing legacy ciphertext permanently unreadable.
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS, dklen=KEY_SIZE)


def encrypt_content(plaintext: str, key: bytes, aad: bytes | None = None) -> dict:
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt returns ciphertext + tag combined
    ct_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
    # Tag is last 16 bytes
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    return {
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "tag": base64.b64encode(tag).decode(),
    }


def decrypt_content(encrypted_data: dict, key: bytes, aad: bytes | None = None) -> str:
    ct = base64.b64decode(encrypted_data["ciphertext"])
    nonce = base64.b64decode(encrypted_data["nonce"])
    tag = base64.b64decode(encrypted_data["tag"]) if encrypted_data.get("tag") else b""
    aesgcm = AESGCM(key)
    # If tag is provided, append it to ciphertext for decryption.
    # Empty tag = legacy format (tag embedded in ciphertext); kept for migration.
    ct_with_tag = ct + tag if tag else ct
    plaintext = aesgcm.decrypt(nonce, ct_with_tag, aad)
    return plaintext.decode("utf-8")
