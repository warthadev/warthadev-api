# descriptjson.py

import base64
import json
import zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# -------- Decode DATA_KEY Base64 --------
def decode_data_key(data_key_b64: str) -> bytes:
    """
    Convert DATA_KEY dari Base64 ke bytes
    """
    return base64.b64decode(data_key_b64.strip())

# -------- Extract data.inner.enc dari ZIP --------
def extract_inner_enc(zip_path: str, inner_filename: str = "data.inner.enc") -> bytes:
    """
    Ambil file data.inner.enc dari package ZIP
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        return zf.read(inner_filename)

# -------- Decrypt AES-GCM --------
def decrypt_aes_gcm(data_key: bytes, enc_bytes: bytes) -> bytes:
    """
    Dekripsi bytes terenkripsi AES-GCM (data.inner.enc)
    """
    iv = enc_bytes[:12]
    ct = enc_bytes[12:]
    aes = AESGCM(data_key)
    return aes.decrypt(iv, ct, None)

# -------- Load JSON dari bytes --------
def load_json_from_bytes(b: bytes):
    """
    Convert bytes hasil decrypt menjadi dictionary JSON
    """
    return json.loads(b)

# -------- Full pipeline helper --------
def decrypt_json_from_zip(zip_path: str, data_key_b64: str) -> dict:
    """
    Full pipeline: decode DATA_KEY, extract inner file, decrypt, load JSON
    """
    data_key = decode_data_key(data_key_b64)
    enc_bytes = extract_inner_enc(zip_path)
    plaintext = decrypt_aes_gcm(data_key, enc_bytes)
    return load_json_from_bytes(plaintext)