import os, re, time, signal, subprocess
from threading import Thread
from werkzeug.serving import run_simple
from dns import doh_resolves

def ensure_cloudflared(CLOUDFLARED_BIN):
    if os.path.exists(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK): return True
    try:
        print("Mengunduh cloudflared...")
        rc = subprocess.run(f"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O {CLOUDFLARED_BIN}", shell=True).returncode
        if rc == 0:
            os.chmod(CLOUDFLARED_BIN,0o755)
            return True
    except Exception as e:
        print("Gagal unduh cloudflared:", e)
    return False

def run_flask_and_tunnel(app, PORT, CLOUDFLARED_BIN, CLOUDFLARE_TIMEOUT=60, DNS_CHECK_TIMEOUT=90, CLOUDFLARED_RESTARTS=3, RETRY_DELAY=2):
    def _run():
        run_simple("127.0.0.1", PORT, app, use_reloader=False, threaded=True)
    Thread(target=_run).start()

    if not ensure_cloudflared(CLOUDFLARED_BIN):
        print("cloudflared tidak tersedia."); return

    restarts = 0
    while restarts < CLOUDFLARED_RESTARTS:
        restarts += 1
        print(f"[TUNNEL] Percobaan {restarts}/{CLOUDFLARED_RESTARTS}")
        proc = subprocess.Popen([CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        start = time.time()
        public_url = None
        while time.time() - start < CLOUDFLARE_TIMEOUT:
            line = proc.stdout.readline()
            if not line: continue
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
            if m:
                public_url = m.group(1)
                break
        if public_url:
            print(f"[TUNNEL] URL ditemukan: {public_url}")
            host = re.sub(r'^https?://', '', public_url).split('/')[0]
            if doh_resolves(host, timeout=3):
                print(f"🌍 URL siap: {public_url}")
                return
        proc.terminate()
        time.sleep(RETRY_DELAY)
    print("❌ Semua percobaan gagal.")