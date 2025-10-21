# app.py - Definisi Aplikasi Flask
import os, logging
from flask import Flask, render_template, send_file, request

# --- Variabel Dinamis (Akan disuntikkan oleh skrip induk) ---
ROOT_PATH = os.environ.get("FLASK_ROOT", "/content")
DECRYPTION_SUCCESS = False
# -----------------------------------------------------------

# Impor Utils (Asumsi utils.py ada di PYTHONPATH atau diimpor di skrip induk)
try:
    from utils import format_size, get_disk_usage, list_dir, _is_within_root
except ImportError:
    # Fallback/Debug jika utils.py tidak diimpor dengan benar
    print("Warning: utils.py not loaded correctly. Using stubs.")
    format_size = lambda x: f"{x} B"
    get_disk_usage = lambda x: (0, 0, 0.0)
    list_dir = lambda x, y: []
    _is_within_root = lambda x, y: True

# Konfigurasi internal Flask
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# Setup direktori
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
TPL_PATH = os.path.join(TEMPLATE_FOLDER, "main.html")

# --- FLASK APP ---
app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")
app.jinja_env.globals.update(format_size=format_size, os_path=os.path)

@app.route("/")
def index():
    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=ROOT_PATH
    
    # Cek batas ROOT_PATH menggunakan fungsi dari utils
    if not _is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path): abs_path=ROOT_PATH
    
    colab_total, colab_used, colab_percent = get_disk_usage(ROOT_PATH)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = get_disk_usage(drive_mount_path)
    
    # Gunakan list_dir dari utils
    files = list_dir(abs_path, ROOT_PATH)
    tpl = "main.html"
    
    if not os.path.exists(TPL_PATH):
        items_html = "".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
        return f"<html><head><title>File Manager Fallback</title></head><body><h3>{abs_path}</h3>{items_html}</body></html>" 
        
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
    
    # Cek batas ROOT_PATH menggunakan fungsi dari utils
    if not _is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
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
