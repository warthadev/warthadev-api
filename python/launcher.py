# python/launcher.py
import os
import time
import logging
from threading import Thread
from werkzeug.serving import run_simple
from .app import create_app
from .tunnel import run_tunnel, TUNNEL_ENABLED

LOG = logging.getLogger("newflask.launcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def start_flask(app, host="127.0.0.1", port=None):
    port = port or int(os.environ.get("NEWFLASK_PORT", "8000"))
    def _run():
        try:
            run_simple(host, port, app, use_reloader=False, threaded=True)
        except Exception:
            LOG.exception("Flask run error")
    t = Thread(target=_run, daemon=True)
    t.start()
    return t

def launch(root_path=None, template_folder=None, port=None, tunnel_attempts=None):
    root_path = root_path or os.environ.get("NEWFLASK_ROOT", "/content")
    port = port or int(os.environ.get("NEWFLASK_PORT", "8000"))
    app = create_app(root_path=root_path, template_folder=template_folder)
    LOG.info("Starting Flask on port %s (root=%s)", port, root_path)
    start_flask(app, port=port)
    if TUNNEL_ENABLED:
        LOG.info("Running tunnel...")
        public = run_tunnel(port, attempts=tunnel_attempts)
        if public:
            LOG.info("Public URL: %s", public)
        else:
            LOG.warning("No public URL obtained.")
    else:
        LOG.info("Tunnel disabled by env.")

if __name__ == "__main__":
    launch()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.info("Launcher terminated.")