import os, re, time, signal, socket, subprocess
from threading import Thread
from werkzeug.serving import run_simple
from config import *
import requests
from server import app

def doh_resolves(hostname, timeout=5):
    urls = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A",
    ]
    headers = {"Accept":"application/dns-json"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=timeout)
            if r.status_code == 200 and r.json().get("Status") == 0 and r.json().get("Answer"):
                return True
        except: continue
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except: return False

def ensure_cloudflared():
    if os.path.exists(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK): return True
    print("Mengunduh cloudflared...")
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    rc = subprocess.run(f"wget -q {url} -O {CLOUDFLARED_BIN}", shell=True).returncode
    if rc != 0: subprocess.run(f"curl -sL {url} -o {CLOUDFLARED_BIN}", shell=True)
    os.chmod(CLOUDFLARED_BIN,0o755)
    return True

def stop_proc(proc):
    if proc and proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        time.sleep(0.5)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

def start_cloudflared(args):
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, preexec_fn=os.setsid)
        return proc
    except Exception as e:
        print("Gagal start cloudflared:", e)
        return None

def run_flask_and_tunnel():
    Thread(target=lambda: run_simple("127.0.0.1", PORT, app, use_reloader=False, threaded=True)).start()

    if not ensure_cloudflared():
        print("❌ Cloudflared gagal diunduh.")
        return

    restarts = 0
    while restarts < CLOUDFLARED_RESTARTS:
        restarts += 1
        print(f"[TUNNEL] Mencoba (attempt {restarts}/{CLOUDFLARED_RESTARTS})...")
        proc = start_cloudflared([CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"])
        if not proc:
            time.sleep(2)
            continue
        public_url = None
        start = time.time()
        while time.time() - start < CLOUDFLARE_TIMEOUT:
            line = proc.stdout.readline()
            if not line: 
                time.sleep(RETRY_DELAY)
                continue
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line.strip())
            if m:
                public_url = m.group(1)
                break
        if not public_url:
            stop_proc(proc)
            continue
        hostname = re.sub(r'^https?://','',public_url).split('/')[0]
        dns_ok = False
        print(f"[DNS] Menunggu {hostname} resolve ...")
        for _ in range(DNS_CHECK_TIMEOUT):
            if doh_resolves(hostname): dns_ok=True; break
            time.sleep(1)
        if dns_ok:
            print("="*50)
            print("✅ URL PUBLIK:", public_url)
            print("="*50)
            return
        else:
            stop_proc(proc)