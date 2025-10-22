# server.py

import os
from werkzeug.serving import run_simple
from flask import Flask, render_template, send_file, request

from . import config # Import konfigurasi
from . import utils # Import fungsi utility

# --- FLASK APP INITIATION ---
app = Flask(__name__, 
            template_folder=config.TEMPLATE_FOLDER, 
            static_folder=config.STATIC_FOLDER_ROOT, 
            static_url_path="/static")
            
# Daftarkan fungsi format_size dan os.path ke Jinja (template)
app.jinja_env.globals.update(format_size=utils.format_size, os_path=os.path)

@app.route("/")
def index():
    # Mengambil path dari parameter query, default ke ROOT_PATH
    req_path = request.args.get("path", config.ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=config.ROOT_PATH
    
    # Validasi path agar tidak keluar dari ROOT_PATH
    if not utils._is_within_root(abs_path) or not os.path.exists(abs_path): abs_path=config.ROOT_PATH
    
    # Ambil penggunaan disk
    colab_total, colab_used, colab_percent = utils.get_disk_usage(config.ROOT_PATH)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = utils.get_disk_usage(drive_mount_path)
    
    # List konten direktori
    files = utils.list_dir(abs_path)
    tpl = "main.html"
    
    # Fallback jika main.html tidak ada (Sama seperti logika asli)
    if not os.path.exists(os.path.join(config.TEMPLATE_FOLDER, tpl)):
        items_html = "".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
        return f"<html><body><h3>{abs_path}</h3>{items_html}</body></html>" 
        
    return render_template(tpl, path=abs_path, root_path=config.ROOT_PATH, files=files,
        colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent,
        drive_total=drive_total, drive_used=drive_used, drive_percent=drive_percent,
        drive_mount_path=drive_mount_path)

@app.route("/file")
def open_file():
    p = request.args.get("path","")
    if not p: return "Path missing",400
    try: abs_path=os.path.abspath(p)
    except: return "Invalid path",400
    
    # Validasi file
    if not utils._is_within_root(abs_path) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return "File cannot be opened.",404
        
    ext=os.path.splitext(abs_path)[1].lower()
    
    # Jika file teks, tampilkan sebagai teks biasa
    if ext in config.TEXT_FILE_EXTENSIONS:
        try:
            with open(abs_path,"r",encoding="utf-8",errors="ignore") as fh: content=fh.read()
            return f"<pre>{content.replace('</','&lt;/')}</pre>"
        except Exception as e: return f"Failed to read file: {e}",500
        
    # Jika bukan teks, kirim sebagai download
    try: return send_file(abs_path, as_attachment=True)
    except Exception as e: return f"Failed to send file: {e}",500

def start_flask_server():
    """Fungsi pembungkus untuk menjalankan Flask server"""
    try: run_simple("127.0.0.1", config.PORT, app, use_reloader=False, threaded=True)
    except Exception as e: print("Flask run error:", e)
