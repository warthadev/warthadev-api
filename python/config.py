import os, logging

ROOT_PATH = os.environ.get("NEWFLASK_ROOT", "/content")
PORT = int(os.environ.get("NEWFLASK_PORT", "8000"))
CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = int(os.environ.get("CLOUDFLARE_TIMEOUT", "60"))
DNS_CHECK_TIMEOUT = int(os.environ.get("DNS_CHECK_TIMEOUT", "90"))
CLOUDFLARED_RESTARTS = int(os.environ.get("CLOUDFLARED_RESTARTS", "3"))
RETRY_DELAY = float(os.environ.get("TUNNEL_RETRY_DELAY", "2"))

logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)