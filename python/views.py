# views.py (Kode FINAL - Mendukung Caching dan AJAX/JSON)
import os, sys
from flask import render_template, send_file, request, jsonify
# Gunakan import absolut di sini karena sys.path sudah diatur di Colab
import utils 
# import cache # <-- TIDAK PERLU diimpor di sini karena sudah disuntikkan via app.py

# Variabel yang akan disuntikkan dari app.py
ROOT_PATH = "/content"
DECRYPTION_SUCCESS = False
TEMPLATE_FOLDER = ""
app = None 
cache = None # <-- BARIS BARU: Variabel untuk menerima modul cache


def index():
    """Route utama untuk menampilkan file manager (digunakan hanya untuk pemuatan halaman awal)."""
    # Pastikan app dan templates sudah disuntikkan sebelum digunakan
    if app is None or TEMPLATE_FOLDER == "": return "Server not fully initialized.", 500

    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=ROOT_PATH
    
    # Keamanan: Pastikan path berada di dalam ROOT_PATH
    if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path): abs_path=ROOT_PATH
    
    # Ambil data disk usage (ini tidak dicache, karena harus real-time)
    colab_total, colab_used, colab_percent = utils.get_disk_usage(ROOT_PATH)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = utils.get_disk_usage(drive_mount_path)
    
    # Panggilan pertama list_dir (akan menggunakan cache jika ada)
    files = utils.list_dir(abs_path, ROOT_PATH)
    tpl = "main.html"
    
    # Logika fallback (HTML mentah)
    if not os.path.exists(os.path.join(TEMPLATE_FOLDER, tpl)):
        items_html = "".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
        return f"<html><body><h3>{abs_path}</h3>{items_html}</body></html>" 
        
    return render_template(tpl, path=abs_path, root_path=ROOT_PATH, files=files,
        colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent,
        drive_total=drive_total, drive_used=drive_used, drive_percent=drive_percent,
        drive_mount_path=drive_mount_path)


def get_dir_data():
    """ROUTE BARU: Mengembalikan data direktori sebagai JSON (untuk panggilan AJAX)."""
    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=ROOT_PATH
    
    # Keamanan: Pastikan path berada di dalam ROOT_PATH
    if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path): abs_path=ROOT_PATH
    
    # Panggilan ke list_dir akan menggunakan cache jika sudah ada
    files = utils.list_dir(abs_path, ROOT_PATH)
    
    return jsonify({
        "status": "success",
        "current_path": abs_path,
        "files": files,
    })


def clear_app_cache():
    """ROUTE BARU: Memicu pembersihan cache aplikasi (dipanggil setelah operasi write/upload)."""
    global cache
    
    if cache is None: return jsonify({"status":"error", "message":"Cache module not initialized"}), 500
    
    # Panggil fungsi pembersihan terpusat dari modul cache
    cache.clear_all_caches()
    
    return jsonify({"status":"success", "message":"Application cache cleared."})


def open_file():
    """Route untuk membuka atau mengunduh file."""
    p = request.args.get("path","")
    if not p: return "Path missing",400
    try: abs_path=os.path.abspath(p)
    except: return "Invalid path",400
    
    # Keamanan: Pastikan path berada di dalam ROOT_PATH
    if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
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
