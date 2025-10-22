import os, sys, time
from flaskapp import create_app
from tunnel import run_flask_and_tunnel

ROOT_PATH = os.environ.get("NEWFLASK_ROOT", "/content")
PORT = int(os.environ.get("NEWFLASK_PORT", "8000"))
CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")

if __name__ == "__main__":
    os.makedirs(ROOT_PATH, exist_ok=True)
    app = create_app(ROOT_PATH)
    run_flask_and_tunnel(app, PORT, CLOUDFLARED_BIN)
    while True:
        time.sleep(1)