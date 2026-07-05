import pytest
from cryptography.exceptions import InvalidTag

from app.crypto import (
    decrypt_content,
    derive_key,
    encrypt_content,
    generate_salt,
)


class TestDeriveKey:
    def test_derive_key_deterministic(self):
        password = "my_secure_password"
        salt = generate_salt()
        key1 = derive_key(password, salt)
        key2 = derive_key(password, salt)
        assert key1 == key2

    def test_derive_key_different_salts(self):
        password = "my_secure_password"
        key1 = derive_key(password, generate_salt())
        key2 = derive_key(password, generate_salt())
        assert key1 != key2


class TestEncryptDecrypt:
    def test_encrypt_decrypt_roundtrip(self):
        key = derive_key("password", generate_salt())
        plaintext = "This is a test message"
        encrypted = encrypt_content(plaintext, key)
        decrypted = decrypt_content(encrypted, key)
        assert decrypted == plaintext

    def test_encrypt_decrypt_empty_string(self):
        key = derive_key("password", generate_salt())
        plaintext = ""
        encrypted = encrypt_content(plaintext, key)
        decrypted = decrypt_content(encrypted, key)
        assert decrypted == plaintext

    def test_encrypt_decrypt_unicode(self):
        key = derive_key("password", generate_salt())
        plaintext = "你好世界 🌍 café naïve résumé"
        encrypted = encrypt_content(plaintext, key)
        decrypted = decrypt_content(encrypted, key)
        assert decrypted == plaintext

    def test_wrong_key_fails_decryption(self):
        key1 = derive_key("password1", generate_salt())
        key2 = derive_key("password2", generate_salt())
        encrypted = encrypt_content("secret", key1)
        with pytest.raises(InvalidTag):
            decrypt_content(encrypted, key2)

    def test_tampered_ciphertext_fails(self):
        key = derive_key("password", generate_salt())
        encrypted = encrypt_content("secret", key)
        import base64

        raw = base64.b64decode(encrypted["ciphertext"])
        tampered = bytes([raw[0] ^ 0xFF]) + raw[1:]
        encrypted["ciphertext"] = base64.b64encode(tampered).decode()
        with pytest.raises(InvalidTag):
            decrypt_content(encrypted, key)
