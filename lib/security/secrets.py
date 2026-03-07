# lib/security/secrets.py
from __future__ import annotations
import os, json, base64, hashlib
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

SECRETS_PATH = Path("/THE_VAULT/jarvis/secrets/.keyring")

class SecretsManager:
    def __init__(self, keyring_path: Path = SECRETS_PATH):
        self.path = keyring_path
        self._key = self._derive_machine_key()
        self._cache: dict[str, str] = {}
        self._load()

    def _derive_machine_key(self) -> bytes:
        """Derive a stable 32-byte key from machine-id and user."""
        try:
            with open("/etc/machine-id", "r") as f:
                mid = f.read().strip()
        except:
            mid = "fallback-machine-id"
        
        user = os.getenv("USER", "default")
        seed = f"{mid}:{user}:jarvis-v2-salt"
        return hashlib.sha256(seed.encode()).digest()

    def _load(self):
        if not self.path.exists():
            return
        try:
            with open(self.path, "rb") as f:
                encrypted_data = f.read()
            if not encrypted_data:
                return
            
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            cipher = Cipher(algorithms.AES(self._key), modes.CFB(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            self._cache = json.loads(plaintext.decode())
        except Exception as e:
            import logging
            logging.getLogger("jarvis.security").error(f"Failed to load secrets: {e}")
            self._cache = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        plaintext = json.dumps(self._cache).encode()
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self._key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        with open(self.path, "wb") as f:
            f.write(iv + ciphertext)
        # Ensure strict permissions
        self.path.chmod(0o600)

    def get(self, name: str) -> str | None:
        return self._cache.get(name)

    def set(self, name: str, value: str):
        self._cache[name] = value
        self._save()

    def has(self, name: str) -> bool:
        return name in self._cache

    def list_keys(self) -> list[str]:
        return list(self._cache.keys())
