# tunnel.py
import os, subprocess, signal, time, re, socket, json
from threading import Thread
import requests
from werkzeug.serving import run_simple

# Variabel yang akan disuntikkan dari app.py
PORT = 8000
app = None # Instance aplikasi Flask
# Konfigurasi Tunnel (diambil dari env jika ada, jika tidak, pakai default app.py)
CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = int(os.environ.get("CLOUDFLARE_TIMEOUT", "60"))
DNS_CHECK_TIMEOUT = int(os.environ.get("DNS_CHECK_TIMEOUT", "90"))
CLOUDFLARED_RESTARTS = int(os.environ.get("CLOUDFLARED_RESTARTS", "3"))
RETRY_DELAY = float(os.environ.get("TUNNEL_RETRY_DELAY", "2"))


# --- DNS CHECK HELPERS (DOH) ---
def doh_resolves(hostname, timeout=5):
    urls = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A",
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=AAAA",
        f"https://dns.google/resolve?name={hostname}&type=AAAA"
    ]
    headers = {"Accept":"application/dns-json"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=timeout)
            if r.status_code == 200:
                try:
                    j = r.json()
                    if j.get("Status") == 0 and j.get("Answer"): return True
                except Exception: continue
        except Exception: continue
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except Exception:
        return False

# --- CLOUDFLARE ENSURE + RUN + RETRY ---
def ensure_cloudflared():
    if os.path.exists(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK): return True
    try:
        print("Mengunduh cloudflared...")
        rc = subprocess.run(f"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O {CLOUDFLARED_BIN}", shell=True).returncode
        if rc!=0:
             rc = subprocess.run(f"curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o {CLOUDFLARED_BIN}", shell=True).returncode
        if rc==0:
            os.chmod(CLOUDFLARED_BIN,0o755)
            return True
        else:
            print("Gagal unduh cloudflared setelah mencoba wget dan curl.")
            return False
    except Exception as e:
        print("Gagal unduh cloudflared:", e)
        return False

def start_cloudflared(proc_args):
    try:
        proc = subprocess.Popen(proc_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid)
        return proc
    except Exception as e:
        print("Gagal start cloudflared:", e)
        return None

def stop_proc(proc):
    try:
        if proc and proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(0.3)
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass

def run_flask_and_tunnel():
    if app is None:
        print("Error: Instance Flask belum disuntikkan ke modul tunnel.")
        return

    def _run():
        try: run_simple("127.0.0.1", PORT, app, use_reloader=False, threaded=True)
        except Exception as e: print("Flask run error:", e)
    t = Thread(target=_run)
    t.start()

    if not ensure_cloudflared():
        print("cloudflared tidak tersedia. Tidak bisa membuat terowongan."); return

    proc = None
    restarts = 0
    public_url = None

    while restarts < CLOUDFLARED_RESTARTS:
        restarts += 1
        print(f"[TUNNEL] Mencoba membuat terowongan (attempt {restarts}/{CLOUDFLARED_RESTARTS})...")
        args = [CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate", "--loglevel", "info", "--edge-ip-version", "auto"]
        proc = start_cloudflared(args)
        if not proc:
            print("[TUNNEL] Gagal start cloudflared, retrying...")
            time.sleep(2)
            continue

        start = time.time()
        public_url = None
        while time.time() - start < CLOUDFLARE_TIMEOUT:
            try: line = proc.stdout.readline()
            except Exception: line = ""
            if not line:
                time.sleep(RETRY_DELAY)
                if proc.poll() is not None: break
                continue
            line_str = line.strip()
            print(line_str)
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line_str)
            if m:
                public_url = m.group(1)
                print(f"[TUNNEL] URL ditemukan di stdout: {public_url}")
                break

        if not public_url or proc.poll() is not None:
            print("[TUNNEL] Tidak dapat menemukan URL atau proses mati. Akan restart cloudflared dan coba lagi.")
            stop_proc(proc)
            time.sleep(2)
            continue

        hostname = re.sub(r'^https?://', '', public_url).split('/')[0]
        print(f"[DNS] Menunggu hostname {hostname} ter-resolve (timeout {DNS_CHECK_TIMEOUT}s)...")
        dns_start = time.time()
        resolved = False
        while time.time() - dns_start < DNS_CHECK_TIMEOUT:
            if doh_resolves(hostname, timeout=3):
                resolved = True
                break
            if proc.poll() is not None:
                print("[DNS] Cloudflared mati saat menunggu DNS. Membatalkan DNS check.")
                break
            print("[DNS] Belum ter-resolve, menunggu 1s lalu retry...")
            time.sleep(1)

        if resolved:
            print("\n" + "="*50)
            print("URL PUBLIK ANDA (dan sudah resolved):")
            print(f"  {public_url}")
            print("="*50 + "\n")
            return
        else:
            print("[DNS] Hostname masih belum ter-resolve setelah timeout atau proses mati. Akan restart cloudflared dan coba lagi.")
            stop_proc(proc)
            time.sleep(2)
            continue

    if proc and proc.poll() is None:
        print("[TUNNEL] Semua percobaan restart habis, tapi proses cloudflared masih berjalan — periksa log di atas.")
    else:
        print("[TUNNEL] Semua percobaan gagal. Tidak ada tunnel aktif.")
