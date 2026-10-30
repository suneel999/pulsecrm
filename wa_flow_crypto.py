"""WhatsApp Flows request decryption / response encryption (Meta AES-128-GCM + RSA-OAEP)."""
from __future__ import annotations

import json
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FlowCryptoError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _load_private_key(private_pem: str, passphrase: str = ""):
    password = passphrase.encode("utf-8") if passphrase else None
    return serialization.load_pem_private_key(
        private_pem.encode("utf-8"),
        password=password,
    )


def decrypt_request(body: dict, private_pem: str, passphrase: str = "") -> dict:
    try:
        encrypted_aes_key = b64decode(body["encrypted_aes_key"])
        encrypted_flow_data = b64decode(body["encrypted_flow_data"])
        initial_vector = b64decode(body["initial_vector"])
    except (KeyError, ValueError) as exc:
        raise FlowCryptoError(400, f"Invalid encrypted payload: {exc}") from exc

    private_key = _load_private_key(private_pem, passphrase)
    try:
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception as exc:
        # 421 asks Meta client to refresh the business public key
        raise FlowCryptoError(421, "Failed to decrypt AES key. Check private key.") from exc

    if len(encrypted_flow_data) < 16:
        raise FlowCryptoError(400, "Encrypted flow data too short.")

    ciphertext = encrypted_flow_data[:-16]
    tag = encrypted_flow_data[-16:]
    aesgcm = AESGCM(aes_key)
    try:
        plain = aesgcm.decrypt(initial_vector, ciphertext + tag, None)
    except Exception as exc:
        raise FlowCryptoError(421, "Failed to decrypt flow data.") from exc

    return {
        "decrypted_body": json.loads(plain.decode("utf-8")),
        "aes_key": aes_key,
        "initial_vector": initial_vector,
    }


def encrypt_response(response: dict, aes_key: bytes, initial_vector: bytes) -> str:
    flipped_iv = bytes((~b) & 0xFF for b in initial_vector)
    aesgcm = AESGCM(aes_key)
    encrypted = aesgcm.encrypt(flipped_iv, json.dumps(response).encode("utf-8"), None)
    return b64encode(encrypted).decode("ascii")
