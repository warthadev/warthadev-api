# config.py

import os, logging

# --- KONFIGURASI ---
ROOT_PATH = os.environ.get("NEWFLASK_ROOT", "/content")
PORT = int(os.environ.get("NEWFLASK_PORT", "8000"))
CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = int(os.environ.get("CLOUDFLARE_TIMEOUT", "60"))  # waktu tunggu awal (detik)
DNS_CHECK_TIMEOUT = int(os.environ.get("DNS_CHECK_TIMEOUT", "90"))  # waktu tunggu saat menunggu DNS propagate
CLOUDFLARED_RESTARTS = int(os.environ.get("CLOUDFLARED_RESTARTS", "3"))  # max restart attempts
RETRY_DELAY = float(os.environ.get("TUNNEL_RETRY_DELAY", "2"))  # delay antar read stdout

# Matikan logging werkzeug (server Flask) agar konsol lebih bersih
logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    # BASE_DIR: Direktori tempat script utama berada
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # Fallback jika dijalankan di lingkungan interaktif/non-file
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR

# Pastikan folder template ada
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
TPL_PATH = os.path.join(TEMPLATE_FOLDER, "main.html")

# Ekstensi file yang dianggap teks untuk dibuka langsung di browser
TEXT_FILE_EXTENSIONS = {'.txt','.py','.csv','.md','.log','.json','.yml','.yaml','.html','.css','.js'}
