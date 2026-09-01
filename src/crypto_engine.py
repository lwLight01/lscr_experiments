import os
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import hmac as crypto_hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

class CryptoEngine:

    def __init__(self):
        self.aesgcm = None

    def set_key(self, key: bytes):

        assert len(key) == 32, f"Expected 32-byte key, got {len(key)}"
        self.aesgcm = AESGCM(key)

    @staticmethod
    def generate_session_key() -> bytes:

        return os.urandom(32)

    @staticmethod
    def derive_key(shared_secret: bytes, salt: bytes, info: bytes) -> bytes:

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
        )
        return hkdf.derive(shared_secret)

    def encrypt(self, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:

        assert self.aesgcm is not None, "Call set_key() first"
        return self.aesgcm.encrypt(nonce, plaintext, aad)

    def decrypt(self, nonce: bytes, ciphertext_with_tag: bytes, aad: bytes) -> bytes | None:

        assert self.aesgcm is not None, "Call set_key() first"
        try:
            return self.aesgcm.decrypt(nonce, ciphertext_with_tag, aad)
        except InvalidTag:
            return None

    @staticmethod
    def compute_hmac(key: bytes, data: bytes) -> bytes:

        h = crypto_hmac.HMAC(key, hashes.SHA256())
        h.update(data)
        return h.finalize()

    @staticmethod
    def compute_state_digest(sk: bytes, sid: bytes, epoch: int,
                              sn_send: int, sn_recv: int, nc: int) -> bytes:

        data = sid + struct.pack('>HIIQ', epoch, sn_send, sn_recv, nc)
        h = crypto_hmac.HMAC(sk, hashes.SHA256())
        h.update(data)
        return h.finalize()

    @staticmethod
    def construct_nonce(epoch: int, sender_id: int, counter: int) -> bytes:

        return struct.pack('>HHQ', epoch, sender_id, counter)
