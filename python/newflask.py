#!/usr/bin/env python3
# newflask.py - versi diperkuat: DNS-check + auto-retry + tunnel restart tanpa restart Flask
import os, sys, math, time, re, shutil, logging, subprocess, signal, socket, json, threading
from threading import Thread, Event, Lock
from werkzeug.serving import run_simple
from flask import Flask, render_template, send_file, request, jsonify

# --- KONFIGURASI ---
ROOT_PATH = os.environ.get("NEWFLASK_ROOT", "/content")
PORT = int(os.environ.get("NEWFLASK_PORT", "8000"))
CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = int(os.environ.get("CLOUDFLARE_TIMEOUT", "60"))  # waktu tunggu awal (detik)
DNS_CHECK_TIMEOUT = int(os.environ.get("DNS_CHECK_TIMEOUT", "90"))  # waktu tunggu saat menunggu DNS propagate
CLOUDFLARED_RESTARTS = int(os.environ.get("CLOUDFLARED_RESTARTS", "3"))  # max restart attempts per cycle
RETRY_DELAY = float(os.environ.get("TUNNEL_RETRY_DELAY", "2"))  # delay antar read stdout
logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

TPL_PATH = os.path.join(TEMPLATE_FOLDER, "main.html")

# --- UTILITY FUNCTIONS (tetap sama) ---
def format_size(size_bytes):
    if size_bytes is None or size_bytes < 0: return "0 B"
    if size_bytes == 0: return "0 B"
    size_name = ("B","KB","MB","GB","TB")
    i = int(math.floor(math.log(size_bytes,1024)))
    p = math.pow(1024,i)
    s = round(size_bytes/p,2)
    return f"{s} {size_name[i]}"

def get_disk_usage(path):
    try:
        if not os.path.exists(path): return 0,0,0.0
        total, used, free = shutil.disk_usage(path)
        percent = (used/total)*100 if total>0 else 0.0
        return total, used, percent
    except: return 0,0,0.0

def _is_within_root(path):
    try:
        return os.path.commonpath([os.path.realpath(ROOT_PATH), os.path.realpath(path)]) == os.path.realpath(ROOT_PATH)
    except: return False

def get_directory_size(start_path='.'):
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(start_path):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    if not os.path.islink(fp): total_size += os.path.getsize(fp)
                except: continue
    except: return -1
    return total_size

def get_file_icon_class(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.mp4','.mkv','.avi','.mov','.wmv']: return "fa-file-video"
    if ext in ['.mp3','.wav','.flac','.ogg']: return "fa-file-audio"
    if ext in ['.jpg','.jpeg','.png','.gif','.bmp','.svg','.webp']: return "fa-file-image"
    if ext in ['.exe','.msi','.deb','.rpm','.apk']: return "fa-box"
    if ext in ['.py','.java','.c','.cpp','.html','.css','.js','.json','.xml','.sh']: return "fa-file-code"
    if ext in ['.zip','.rar','.7z','.tar','.gz','.tgz']: return "fa-file-archive"
    if ext in ['.pdf']: return "fa-file-pdf"
    if ext in ['.doc','.docx']: return "fa-file-word"
    if ext in ['.xls','.xlsx','.csv']: return "fa-file-excel"
    if ext in ['.ppt','.pptx']: return "fa-file-powerpoint"
    if ext in ['.txt','.log','.md','.ini','.cfg','.yml','.yaml']: return "fa-file-alt"
    return "fa-file"

def list_dir(path):
    files=[]
    try:
        if not os.path.exists(path): return files
        for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower())):
            full_path = os.path.join(path, name)
            if os.path.islink(full_path) and not _is_within_root(full_path): continue
            is_dir = os.path.isdir(full_path)
            size_bytes, size_formatted, icon_class = 0,"","fa-file"
            if is_dir:
                size_bytes = get_directory_size(full_path)
                size_formatted = format_size(size_bytes) if size_bytes>=0 else "Error"
                icon_class = "fa-folder"
            else:
                try:
                    stat = os.stat(full_path)
                    size_bytes = stat.st_size
                    size_formatted = format_size(size_bytes)
                    icon_class = get_file_icon_class(name)
                except: size_formatted="Error"
            files.append({
                "name": name, "is_dir": is_dir, "full_path": full_path,
                "size": size_formatted, "size_bytes": size_bytes, "icon_class": icon_class
            })
    except Exception as e:
        files.append({"name":f"ERROR: {e}", "is_dir":False,"full_path":"","size":"","icon_class":"fa-exclamation-triangle"})
    return files

# --- FLASK APP ---
app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")
app.jinja_env.globals.update(format_size=format_size, os_path=os.path)

@app.route("/")
def index():
    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=ROOT_PATH
    if not _is_within_root(abs_path) or not os.path.exists(abs_path): abs_path=ROOT_PATH
    colab_total, colab_used, colab_percent = get_disk_usage(ROOT_PATH)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = get_disk_usage(drive_mount_path)
    files = list_dir(abs_path)
    tpl = "main.html"
    if not os.path.exists(os.path.join(TEMPLATE_FOLDER, tpl)):
        items_html = "".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
        return f"<html><body><h3>{abs_path}</h3>{items_html}</body></html>"
    return render_template(tpl, path=abs_path, root_path=ROOT_PATH, files=files,
        colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent,
        drive_total=drive_total, drive_used=drive_used, drive_percent=drive_percent,
        drive_mount_path=drive_mount_path)

@app.route("/file")
def open_file():
    p = request.args.get("path","")
    if not p: return "Path missing",400
    try: abs_path=os.path.abspath(p)
    except: return "Invalid path",400
    if not _is_within_root(abs_path) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return "File cannot be opened.",404
    text_exts={'.txt','.py','.csv','.md','.log','.json','.yml','.yaml','.html','.css','.js'}
    ext=os.path.splitext(abs_path)[1].lower()
    if ext in text_exts:
        try:
            with open(abs_path,"r",encoding="utf-8",errors="ignore") as fh: content=fh.read()
            return f"<pre>{content.replace('</','&lt;/')}</pre>"
        except Exception as e: return f"Failed to read file: {e}",500
    try: return send_file(abs_path, as_attachment=True)
    except Exception as e: return f"Failed to send file: {e}",500

# --- DNS CHECK HELPERS (DOH) ---
def doh_resolves(hostname, timeout=5):
    import requests
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
                    if j.get("Status") == 0 and j.get("Answer"):
                        return True
                except Exception: continue
        except Exception: continue
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except Exception:
        return False

# --- CLOUDFLARED HELPERS (tetap) ---
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

# --- Tunnel Manager: mengelola cloudflared independen dari Flask ---
class TunnelManager:
    def __init__(self):
        self.proc = None
        self.public_url = None
        self.hostname = None
        self._thread = None
        self._stop_event = Event()
        self._restart_request = Event()
        self._lock = Lock()
        self.restarts = 0

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                print("[TUNNEL-MGR] Tunnel manager already running.")
                return
            self._stop_event.clear()
            self._restart_request.clear()
            self._thread = Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            print("[TUNNEL-MGR] Started tunnel manager thread.")

    def stop(self):
        print("[TUNNEL-MGR] Stop requested.")
        self._stop_event.set()
        # kill current proc if any
        with self._lock:
            if self.proc:
                stop_proc(self.proc)
        if self._thread:
            self._thread.join(timeout=3)

    def request_restart(self):
        print("[TUNNEL-MGR] Restart requested.")
        # ask the loop to restart immediately: sets flag and kills current proc
        self._restart_request.set()
        with self._lock:
            if self.proc:
                stop_proc(self.proc)

    def _run_loop(self):
        if not ensure_cloudflared():
            print("[TUNNEL-MGR] cloudflared unavailable, aborting manager.")
            return

        cycle_attempts = 0
        # Continually ensure a live tunnel unless stop requested
        while not self._stop_event.is_set():
            cycle_attempts += 1
            self.restarts = 0
            success = False

            while self.restarts < CLOUDFLARED_RESTARTS and not self._stop_event.is_set() and not self._restart_request.is_set():
                self.restarts += 1
                print(f"[TUNNEL] Starting cloudflared (attempt {self.restarts}/{CLOUDFLARED_RESTARTS})...")
                args = [CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate", "--loglevel", "info", "--edge-ip-version", "auto"]
                proc = start_cloudflared(args)
                with self._lock:
                    self.proc = proc
                    self.public_url = None
                    self.hostname = None

                if not proc:
                    print("[TUNNEL] Failed to spawn cloudflared.")
                    time.sleep(2)
                    continue

                start_time = time.time()
                found = False
                # read stdout to find trycloudflare url
                try:
                    while time.time() - start_time < CLOUDFLARE_TIMEOUT and not self._stop_event.is_set() and not self._restart_request.is_set():
                        line = proc.stdout.readline()
                        if not line:
                            time.sleep(RETRY_DELAY)
                            if proc.poll() is not None:
                                print("[TUNNEL] cloudflared died unexpectedly while waiting for URL.")
                                break
                            continue
                        line = line.strip()
                        print("[cloudflared] " + line)
                        m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
                        if m:
                            url = m.group(1)
                            with self._lock:
                                self.public_url = url
                                self.hostname = re.sub(r'^https?://', '', url).split('/')[0]
                            found = True
                            print(f"[TUNNEL] Found public URL: {url}")
                            break
                except Exception as e:
                    print("[TUNNEL] Exception reading cloudflared stdout:", e)

                # If URL found, wait for DNS resolve
                if found and self.public_url:
                    dns_deadline = time.time() + DNS_CHECK_TIMEOUT
                    resolved = False
                    while time.time() < dns_deadline and not self._stop_event.is_set() and not self._restart_request.is_set():
                        if doh_resolves(self.hostname, timeout=3):
                            resolved = True
                            break
                        if proc.poll() is not None:
                            print("[DNS] cloudflared died while waiting for DNS.")
                            break
                        print("[DNS] Not resolved yet, retrying in 1s...")
                        time.sleep(1)

                    if resolved:
                        print("\n" + "="*50)
                        print("URL PUBLIK ANDA (dan sudah resolved):")
                        print(f"  {self.public_url}")
                        print("="*50 + "\n")
                        # Now keep monitoring: if proc dies or restart requested -> break to restart loop
                        while proc.poll() is None and not self._stop_event.is_set() and not self._restart_request.is_set():
                            time.sleep(1)
                        if self._restart_request.is_set():
                            print("[TUNNEL] Restart requested: will restart cloudflared now.")
                        elif proc.poll() is not None:
                            print("[TUNNEL] cloudflared process ended, will attempt restart.")
                        # cleanup and continue outer restart logic
                        stop_proc(proc)
                        with self._lock:
                            self.proc = None
                            self.public_url = None
                            self.hostname = None
                        # clear restart flag for next cycle
                        self._restart_request.clear()
                        continue
                    else:
                        print("[TUNNEL] DNS not resolved within timeout or cloudflared died. Restarting cloudflared...")
                        stop_proc(proc)
                        with self._lock:
                            self.proc = None
                            self.public_url = None
                            self.hostname = None
                        # short wait then retry (counted by restarts loop)
                        time.sleep(2)
                        continue
                else:
                    print("[TUNNEL] Could not obtain URL. Will retry cloudflared.")
                    try:
                        stop_proc(proc)
                    except:
                        pass
                    with self._lock:
                        self.proc = None
                        self.public_url = None
                        self.hostname = None
                    time.sleep(2)
                    continue

            # if here, either retries exhausted or restart requested or stop requested
            if self._stop_event.is_set():
                print("[TUNNEL-MGR] stop_event set, exiting manager.")
                break
            if self._restart_request.is_set():
                # clear flag and loop to start new attempt immediately
                self._restart_request.clear()
                print("[TUNNEL-MGR] immediate restart requested; starting new cycle.")
                continue
            # exhausted attempts
            print("[TUNNEL-MGR] exhausted cloudflared restart attempts in this cycle.")
            # wait a bit before trying a new cycle to avoid busy loop
            time.sleep(5)
        # end while
        print("[TUNNEL-MGR] manager loop terminated.")

    def get_status(self):
        with self._lock:
            return {
                "running": (self.proc is not None and self.proc.poll() is None),
                "public_url": self.public_url,
                "hostname": self.hostname,
                "restarts_in_cycle": self.restarts
            }

# instantiate manager
tunnel_manager = TunnelManager()

# --- Flask endpoints to control tunnel (new) ---
@app.route("/tunnel/status")
def tunnel_status():
    st = tunnel_manager.get_status()
    return jsonify(st)

@app.route("/tunnel/restart", methods=["POST","GET"])
def tunnel_restart():
    # trigger restart asynchronously
    tunnel_manager.request_restart()
    return jsonify({"status":"restarting_triggered","message":"Tunnel restart requested. Flask tetap berjalan. Periksa /tunnel/status untuk URL baru."})

@app.route("/tunnel/stop", methods=["POST","GET"])
def tunnel_stop():
    tunnel_manager.stop()
    return jsonify({"status":"stopped","message":"Tunnel manager stop requested. cloudflared killed. To start again call /tunnel/start."})

@app.route("/tunnel/start", methods=["POST","GET"])
def tunnel_start():
    tunnel_manager.start()
    return jsonify({"status":"started","message":"Tunnel manager started."})

# --- run function (tetap kompatibel) ---
def run_flask_and_tunnel():
    # start flask
    def _run():
        try: run_simple("127.0.0.1", PORT, app, use_reloader=False, threaded=True)
        except Exception as e: print("Flask run error:", e)
    t = Thread(target=_run, daemon=True)
    t.start()

    # start tunnel manager
    tunnel_manager.start()
    print("[MAIN] Flask started and Tunnel manager started (separate threads).")

# --- MAIN ---
if __name__=="__main__":
    print(f"Starting newflask.py -> ROOT_PATH={ROOT_PATH} PORT={PORT}")
    os.makedirs(ROOT_PATH,exist_ok=True)
    try:
        run_flask_and_tunnel()
        print("Menjaga program tetap hidup (Ctrl+C untuk keluar)...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminated. Stopping tunnel manager...")
        tunnel_manager.stop()
        sys.exit(0)