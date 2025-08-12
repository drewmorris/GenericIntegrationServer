from __future__ import annotations

import json
import os
from typing import Any, Dict

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("CREDENTIALS_SECRET_KEY")
    if not key:
        # Dev fallback – insecure default; replace in prod
        key = Fernet.generate_key().decode("utf-8")
        os.environ["CREDENTIALS_SECRET_KEY"] = key
    return Fernet(key.encode("utf-8"))


def encrypt_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    f = _get_fernet()
    data = json.dumps(payload).encode("utf-8")
    token = f.encrypt(data).decode("utf-8")
    return {"_enc": token}


def maybe_decrypt_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload, dict) and "_enc" in payload:
        f = _get_fernet()
        data = f.decrypt(str(payload["_enc"]).encode("utf-8"))
        return json.loads(data.decode("utf-8"))
    return payload 