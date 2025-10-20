import os, time
from threading import Thread
from werkzeug.serving import run_simple
from wartha_api_app.app import create_app
from wartha_api_app.tunnel import run_tunnel

ROOT_PATH = os.environ.get("WARTHA_ROOT", "/content")
PORT = int(os.environ.get("WARTHA_PORT", "8000"))

def run_flask(app):
    try:
        run_simple("127.0.0.1", PORT, app, use_reloader=False, threaded=True)
    except Exception as e:
        print("Flask run error:", e)

def run_flask_and_tunnel():
    app = create_app(root_path=ROOT_PATH)
    t = Thread(target=run_flask, args=(app,))
    t.daemon = True
    t.start()
    time.sleep(0.2)
    print(f"[INFO] Flask started on http://127.0.0.1:{PORT}")
    # Jalankan tunnel (blocking) — akan print URL ketika ready
    run_tunnel(PORT)

if __name__ == "__main__":
    os.makedirs(ROOT_PATH, exist_ok=True)
    print(f"[START] wartha_api_app -> ROOT_PATH={ROOT_PATH} PORT={PORT}")
    try:
        run_flask_and_tunnel()
        print("Menjaga program tetap hidup (Ctrl+C untuk keluar)...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminated.")