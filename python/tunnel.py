# python/tunnel.py
import os
import re
import time
import signal
import subprocess
import logging
from threading import Thread
from .utils import doh_resolves

LOG = logging.getLogger("newflask.tunnel")
logging = logging.getLogger()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TUNNEL_ENABLED = os.environ.get("TUNNEL_ENABLED", "1") not in ("0", "false", "False")
CLOUDFLARED_BIN = os.path.join(os.getcwd(), os.environ.get("CLOUDFLARED_BIN_NAME", "cloudflared-linux-amd64"))
CLOUDFLARE_TIMEOUT = int(os.environ.get("CLOUDFLARE_TIMEOUT", "60"))
DNS_CHECK_TIMEOUT = int(os.environ.get("DNS_CHECK_TIMEOUT", "90"))
CLOUDFLARED_RESTARTS = int(os.environ.get("CLOUDFLARED_RESTARTS", "3"))
RETRY_DELAY = float(os.environ.get("TUNNEL_RETRY_DELAY", "0.5"))

def ensure_cloudflared(bin_path=None):
    bin_path = bin_path or CLOUDFLARED_BIN
    try:
        if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
            return bin_path
        LOG.info("Mengunduh cloudflared...")
        wget_cmd = f"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O {bin_path}"
        curl_cmd = f"curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o {bin_path}"
        rc = subprocess.run(wget_cmd, shell=True).returncode
        if rc != 0:
            rc = subprocess.run(curl_cmd, shell=True).returncode
        if rc == 0 and os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
            LOG.info("cloudflared siap.")
            return bin_path
        LOG.warning("Gagal unduh cloudflared.")
        return None
    except Exception:
        LOG.exception("ensure_cloudflared:")
        return None

def start_cloudflared(proc_args):
    try:
        proc = subprocess.Popen(proc_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid)
        return proc
    except Exception:
        LOG.exception("start_cloudflared:")
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

def run_tunnel(port, attempts=None, bin_path=None, announce_cb=None):
    """
    Non-blocking: jalankan loop percobaan tunnel. Kembalikan public_url bila berhasil, else None.
    announce_cb(public_url) akan dipanggil saat URL ditemukan.
    """
    if not TUNNEL_ENABLED:
        LOG.info("TUNNEL disabled by env.")
        return None

    bin_path = ensure_cloudflared(bin_path) or bin_path or CLOUDFLARED_BIN
    if not bin_path:
        LOG.error("cloudflared tidak tersedia.")
        return None

    restarts = 0
    max_restarts = attempts or CLOUDFLARED_RESTARTS

    while restarts < max_restarts:
        restarts += 1
        LOG.info(f"[TUNNEL] mencoba terowongan (attempt {restarts}/{max_restarts})")
        args = [bin_path, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate", "--loglevel", "info", "--edge-ip-version", "auto"]
        proc = start_cloudflared(args)
        if not proc:
            LOG.warning("Gagal start cloudflared, retrying...")
            time.sleep(2)
            continue

        start = time.time()
        public_url = None
        while time.time() - start < CLOUDFLARE_TIMEOUT:
            if proc.poll() is not None:
                LOG.warning("cloudflared mati tak terduga.")
                break
            try:
                if proc.stdout is None:
                    time.sleep(RETRY_DELAY)
                    continue
                line = proc.stdout.readline()
            except Exception:
                line = ""
            if not line:
                time.sleep(RETRY_DELAY)
                continue
            LOG.info(line.strip())
            m = re.search(r'https?://[^\s"\'<>]*?trycloudflare\.com(?:[:/]\S*)?', line, re.IGNORECASE)
            if m:
                public_url = m.group(0).strip().rstrip('.,;')
                LOG.info("Ditemukan public_url: %s", public_url)
                if announce_cb:
                    try:
                        announce_cb(public_url)
                    except Exception:
                        pass
                break

        if not public_url or proc.poll() is not None:
            LOG.warning("Tidak dapat menemukan URL atau proses mati. Restarting...")
            stop_proc(proc)
            time.sleep(2)
            continue

        hostname = re.sub(r'^https?://', '', public_url).split('/')[0].split(':')[0]
        LOG.info("Menunggu DNS resolve untuk %s", hostname)
        dns_start = time.time()
        resolved = False
        while time.time() - dns_start < DNS_CHECK_TIMEOUT:
            if proc.poll() is not None:
                LOG.warning("cloudflared mati saat menunggu DNS.")
                break
            if doh_resolves(hostname, timeout=3):
                resolved = True
                break
            time.sleep(1)
        if resolved:
            LOG.info("Tunnel ready: %s", public_url)
            # biarkan proc berjalan
            return public_url
        else:
            LOG.warning("Hostname belum resolve. Restarting...")
            stop_proc(proc)
            time.sleep(2)
            continue

    LOG.error("Semua percobaan tunnel gagal.")
    return None