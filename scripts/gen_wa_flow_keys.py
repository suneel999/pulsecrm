#!/usr/bin/env python3
"""Generate RSA key pair for WhatsApp Flows encryption."""
from __future__ import annotations

import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "secrets"
PRIVATE = SECRETS / "wa_flow_private.pem"
PUBLIC = SECRETS / "wa_flow_public.pem"


def main() -> int:
    SECRETS.mkdir(parents=True, exist_ok=True)
    if PRIVATE.exists() and "--force" not in sys.argv:
        print(f"Already exists: {PRIVATE}")
        print("Re-run with --force to overwrite (you must re-upload public key to Meta).")
        return 1

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    PRIVATE.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    PUBLIC.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Wrote {PRIVATE}")
    print(f"Wrote {PUBLIC}")
    print()
    print("Next: upload public key to Meta (see WHATSAPP_FLOW.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
