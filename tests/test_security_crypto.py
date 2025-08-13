import os
from backend.security.crypto import encrypt_dict, maybe_decrypt_dict
from backend.security.redact import mask_secrets


def test_encrypt_decrypt_roundtrip():
    os.environ.setdefault("CREDENTIALS_SECRET_KEY", "ZHVtbXktZG9ub3QtdXNlLXRoaXMtaW4tcHJvZAo=" )
    payload = {"access_token": "secret", "nested": {"api_key": "sk-xyz"}}
    enc = encrypt_dict(payload)
    assert isinstance(enc, dict) and "_enc" in enc
    dec = maybe_decrypt_dict(enc)
    assert dec == payload


def test_mask_secrets():
    data = {
        "token": "a",
        "password": "b",
        "nested": {"api_key": "c", "normal": "d"},
        "list": [{"client_secret": "e"}, {"normal": "f"}],
    }
    masked = mask_secrets(data)
    assert masked["token"] == "***"
    assert masked["password"] == "***"
    assert masked["nested"]["api_key"] == "***"
    assert masked["nested"]["normal"] == "d"
    assert masked["list"][0]["client_secret"] == "***" 