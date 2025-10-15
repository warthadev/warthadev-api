# descriptjson.py
import zipfile, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def decrypt_json_from_zip(zip_path: str, data_key: bytes):
    """
    Buka ZIP terenkripsi berisi data.inner.enc dan dekripsi pakai data_key.
    Return JSON dict.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        inner_bytes = zf.read("data.inner.enc")

    iv = inner_bytes[:12]
    ct = inner_bytes[12:]

    aes = AESGCM(data_key)
    plaintext = aes.decrypt(iv, ct, None)
    return json.loads(plaintext)