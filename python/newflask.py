import os, sys, math, time, re, shutil, logging, subprocess
from threading import Thread
from werkzeug.serving import run_simple
from flask import Flask, render_template, send_file, request

# --- KONFIGURASI ---
ROOT_PATH = os.environ.get("NEWFLASK_ROOT", "/content")
PORT = int(os.environ.get("NEWFLASK_PORT", "8000"))
CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = int(os.environ.get("NEWFLARE_TIMEOUT", "60"))
MONITOR_INTERVAL = int(os.environ.get("NEWFLARE_MONITOR_INTERVAL", "5"))

logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
if not os.path.isdir(TEMPLATE_FOLDER):
    os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

# --- FUNGSI UTILITY ---
def format_size(size_bytes):
    if size_bytes is None or size_bytes < 0: return "0 B"
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_disk_usage(path):
    try:
        if not os.path.exists(path): return 0, 0, 0.0
        total, used, free = shutil.disk_usage(path)
        percent = (used / total) * 100 if total > 0 else 0.0
        return total, used, percent
    except Exception:
        return 0, 0, 0.0

def _is_within_root(path):
    try:
        real_root = os.path.realpath(ROOT_PATH)
        real_path = os.path.realpath(path)
        return os.path.commonpath([real_root, real_path]) == real_root
    except Exception:
        return False

def get_directory_size(start_path='.'):
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(start_path):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    if not os.path.islink(fp): total_size += os.path.getsize(fp)
                except Exception:
                    continue
    except Exception:
        return -1
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
    files = []
    try:
        if not os.path.exists(path): return files
        for name in sorted(os.listdir(path), key=lambda x: x.lower()):
            full_path = os.path.join(path, name)
            if os.path.islink(full_path) and not _is_within_root(full_path): continue
            is_dir = os.path.isdir(full_path)
            size_bytes, size_formatted, icon_class = 0, "", "fa-file"
            if is_dir:
                size_bytes = get_directory_size(full_path)
                size_formatted = format_size(size_bytes) if size_bytes >= 0 else "Error"
                icon_class = "fa-folder"
            else:
                try:
                    stat = os.stat(full_path)
                    size_bytes = stat.st_size
                    size_formatted = format_size(size_bytes)
                    icon_class = get_file_icon_class(name)
                except Exception:
                    size_formatted = "Error"
            files.append({
                "name": name, "is_dir": is_dir, "full_path": full_path,
                "size": size_formatted, "size_bytes": size_bytes, "icon_class": icon_class
            })
    except Exception as e:
        files.append({"name": f"ERROR: {e}", "is_dir": False, "full_path": "", "size": "", "icon_class": "fa-exclamation-triangle"})
    return files

# --- APLIKASI FLASK ---
app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")
app.jinja_env.globals.update(format_size=format_size, os_path=os.path)

@app.route("/")
def index():
    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path = os.path.abspath(req_path)
    except Exception: abs_path = ROOT_PATH
    if not _is_within_root(abs_path) or not os.path.exists(abs_path): abs_path = ROOT_PATH
    colab_total, colab_used, colab_percent = get_disk_usage(ROOT_PATH)
    drive_mount_path = os.path.join(ROOT_PATH, "drive")
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
    p = request.args.get("path", "")
    if not p: return "Path missing", 400
    try: abs_path = os.path.abspath(p)
    except Exception: return "Invalid path", 400
    if not _is_within_root(abs_path) or not os.path.exists(abs_path) or not os.path.isfile(abs_path): return "File cannot be opened.", 404
    text_exts = {'.txt','.py','.csv','.md','.log','.json','.yml','.yaml','.html','.css','.js'}
    ext = os.path.splitext(abs_path)[1].lower()
    if ext in text_exts:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh: content = fh.read()
            safe_content = content.replace("</", "&lt;/")
            return f"<pre>{safe_content}</pre>"
        except Exception as e: return f"Failed to read file: {e}", 500
    try: return send_file(abs_path, as_attachment=True)
    except Exception as e: return f"Failed to send file: {e}", 500

# --- CLOUDFLARE TUNNEL ---
def ensure_cloudflared():
    if os.path.exists(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK): return True
    try:
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        result = subprocess.run(["wget","-q",download_url,"-O",CLOUDFLARED_BIN], capture_output=True)
        if result.returncode != 0:
            result = subprocess.run(["curl","-sL",download_url,"-o",CLOUDFLARED_BIN], capture_output=True)
        if result.returncode != 0: return False
        os.chmod(CLOUDFLARED_BIN,0o755)
        return True
    except Exception: return False

def _kill_existing_cloudflared():
    try:
        p = subprocess.run(["pgrep","-f",CLOUDFLARED_BIN], capture_output=True)
        if p.returncode == 0 and p.stdout:
            for pid in p.stdout.decode().strip().split():
                try: subprocess.run(["kill","-9",pid], check=False)
                except Exception: pass
    except Exception: pass