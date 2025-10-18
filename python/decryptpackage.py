# decryptpackage.py — Clean version tanpa upload
import zipfile, base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def decrypt_package(zip_path: str, data_key_b64: str, output_dir: str = "/tmp/decrypted_files") -> str:
    data_key = base64.b64decode(data_key_b64)
    zip_path = Path(zip_path)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        enc_name = next((n for n in zf.namelist() if n.endswith("data.inner.enc")), None)
        if not enc_name:
            raise SystemExit("Missing data.inner.enc")
        enc_data = zf.read(enc_name)

    nonce, ciphertext, tag = enc_data[:12], enc_data[12:-16], enc_data[-16:]
    plaintext = AESGCM(data_key).decrypt(nonce, ciphertext + tag, None)
    Path("inner_bundle.zip").write_bytes(plaintext)

    out_dir = Path(output_dir)
    out_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile("inner_bundle.zip", "r") as inner_zip:
        inner_zip.extractall(out_dir)
    
    return str(out_dir)