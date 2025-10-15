# deskripkey.py
import json, base64
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# -------- helpers Base64 ----------
def std_b64_encode(b: bytes) -> str:
    return base64.b64encode(b).decode()

def std_b64_decode(s: str) -> bytes:
    s = s.strip().replace("\n", "").replace(" ", "")
    missing_padding = len(s) % 4
    if missing_padding != 0:
        s += "=" * (4 - missing_padding)
    return base64.b64decode(s)

def urlsafe_b64_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def urlsafe_b64_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

# -------- scrypt + AESGCM ----------
def derive_kek_scrypt(passphrase: bytes, salt: bytes, length=32, n=2**14, r=8, p=1):
    kdf = Scrypt(salt=salt, length=length, n=n, r=r, p=p, backend=default_backend())
    return kdf.derive(passphrase)

def unwrap_once(blob_obj, passphrase_bytes):
    salt = urlsafe_b64_decode(blob_obj["scrypt"]["salt"])
    n = blob_obj["scrypt"]["n"]; r = blob_obj["scrypt"]["r"]; p = blob_obj["scrypt"]["p"]
    iv = urlsafe_b64_decode(blob_obj["iv"])
    ct = urlsafe_b64_decode(blob_obj["ct"])
    kek = derive_kek_scrypt(passphrase_bytes, salt, length=32, n=n, r=r, p=p)
    aes = AESGCM(kek)
    plain = aes.decrypt(iv, ct, None)
    return plain

def multi_unwrap(token_b64: str, passphrase: bytes):
    meta = json.loads(urlsafe_b64_decode(token_b64))
    current = None
    for entry in reversed(meta["rounds"]):
        if current is None:
            plain = unwrap_once(entry, passphrase)
            current = plain
        else:
            plain = unwrap_once(entry, passphrase)
            current = plain
    return current