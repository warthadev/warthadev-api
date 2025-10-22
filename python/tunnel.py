# tunnel.py
import os, subprocess, re, time, threading, signal
from .dns import doh_resolves
from .utils import kill_proc_group

CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = int(os.environ.get("CLOUDFLARE_TIMEOUT","60"))
DNS_CHECK_TIMEOUT = int(os.environ.get("DNS_CHECK_TIMEOUT","90"))
MAX_RESTARTS = int(os.environ.get("CLOUDFLARED_RESTARTS","3"))
RETRY_DELAY = float(os.environ.get("TUNNEL_RETRY_DELAY","1"))

class TunnelManager:
    def __init__(self):
        self.proc = None
        self.thread = None
        self.public_url = None
        self._lock = threading.Lock()
        self._stop_requested = False
        self.restarts = 0

    def ensure_bin(self):
        if os.path.exists(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK):
            return True
        try:
            rc = subprocess.run(f"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O {CLOUDFLARED_BIN}", shell=True).returncode
            if rc != 0:
                rc = subprocess.run(f"curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o {CLOUDFLARED_BIN}", shell=True).returncode
            if rc == 0:
                os.chmod(CLOUDFLARED_BIN, 0o755)
                return True
            return False
        except Exception:
            return False

    def _start_proc(self, port):
        args = [CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate", "--loglevel", "info", "--edge-ip-version", "auto"]
        try:
            self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid)
            return True
        except Exception as e:
            self.proc = None
            return False

    def _read_until_url(self, timeout):
        if not self.proc:
            return None
        start = time.time()
        while time.time() - start < timeout:
            line = None
            try:
                line = self.proc.stdout.readline()
            except Exception:
                pass
            if not line:
                time.sleep(RETRY_DELAY)
                if self.proc.poll() is not None:
                    break
                continue
            line = line.strip()
            # trycloudflare link
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
            if m:
                return m.group(1)
        return None

    def _dns_wait(self, hostname, timeout):
        start = time.time()
        while time.time() - start < timeout:
            if doh_resolves(hostname, timeout=3):
                return True
            if self.proc and self.proc.poll() is not None:
                return False
            time.sleep(1)
        return False

    def start(self, port):
        with self._lock:
            if self.proc and self.proc.poll() is None:
                return {"ok": True, "url": self.public_url, "msg": "Already running"}
            if not self.ensure_bin():
                return {"ok": False, "msg": "cloudflared binary not available"}
            self._stop_requested = False
            self.restarts = 0
            while self.restarts < MAX_RESTARTS and not self._stop_requested:
                self.restarts += 1
                ok = self._start_proc(port)
                if not ok:
                    time.sleep(1)
                    continue
                url = self._read_until_url(CLOUDFLARE_TIMEOUT)
                if not url or (self.proc and self.proc.poll() is not None):
                    # failed: stop and retry
                    try:
                        if self.proc:
                            kill_proc_group(self.proc.pid)
                    except:
                        pass
                    time.sleep(1)
                    continue
                hostname = url.replace("https://","").split("/")[0]
                if self._dns_wait(hostname, DNS_CHECK_TIMEOUT):
                    self.public_url = url
                    return {"ok": True, "url": url}
                else:
                    # stop and retry
                    try:
                        if self.proc:
                            kill_proc_group(self.proc.pid)
                    except:
                        pass
                    time.sleep(1)
                    continue
            return {"ok": False, "msg": "All attempts failed"}

    def stop(self):
        with self._lock:
            self._stop_requested = True
            if self.proc:
                try:
                    kill_proc_group(self.proc.pid)
                except:
                    pass
                self.proc = None
            self.public_url = None
            return {"ok": True}

    def status(self):
        with self._lock:
            running = self.proc is not None and (self.proc.poll() is None)
            return {"running": running, "url": self.public_url, "restarts": self.restarts}