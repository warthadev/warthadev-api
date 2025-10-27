# views.py (Kode FINAL yang Benar)
import os, sys
from flask import render_template, send_file, request, jsonify
# Gunakan import absolut di sini karena sys.path sudah diatur di Colab
import utils 

# Variabel yang akan disuntikkan dari app.py
ROOT_PATH = "/content"
DECRYPTION_SUCCESS = False
TEMPLATE_FOLDER = ""
app = None # Biarkan ini None saat import!


def index():
    """Route utama untuk menampilkan file manager."""
    # Pastikan app dan templates sudah disuntikkan sebelum digunakan
    if app is None or TEMPLATE_FOLDER == "": return "Server not fully initialized.", 500

    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=ROOT_PATH
    
    # Keamanan: Pastikan path berada di dalam ROOT_PATH
    if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path): abs_path=ROOT_PATH
    
    # Ambil Disk Usage (tidak ada cache di sini, dihitung langsung)
    colab_total, colab_used, colab_percent = utils.get_disk_usage(ROOT_PATH)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = utils.get_disk_usage(drive_mount_path)
    
    # Ambil daftar file
    files = utils.list_dir(abs_path, ROOT_PATH)
    tpl = "main.html"
    
    # Logika fallback (HTML mentah)
    if not os.path.exists(os.path.join(TEMPLATE_FOLDER, tpl)):
        items_html = "\n".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
        return f"<html><body><h3>{abs_path}</h3>{items_html}</body></html>" 
        
    return render_template(tpl, path=abs_path, root_path=ROOT_PATH, files=files,
        colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent,
        drive_total=drive_total, drive_used=drive_used, drive_percent=drive_percent,
        drive_mount_path=drive_mount_path, 
        # PERBAIKAN: Menyuntikkan format_size ke template context
        format_size=utils.format_size)


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
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Tampilkan konten dalam format teks
            return f"<pre style='white-space: pre-wrap;'>{content}</pre>", 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            return f"Error reading file: {e}", 500
    else:
        # File biner/lainnya: Langsung diunduh/dibuka browser
        return send_file(abs_path)
        
        
# --- ⭐️ FUNGSI BARU: THUMBNAIL SERVICE ---
def get_thumbnail():
    """Route untuk mendapatkan thumbnail, memanggil generate_thumbnail di utils."""
    p = request.args.get("path", "")
    if not p: return "Path missing", 400
    try: abs_path = os.path.abspath(p)
    except: return "Invalid path", 400

    # 1. Pengecekan Keamanan
    if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return "File not found or access denied.", 404

    # 2. Proses atau Ambil dari Cache (Logika hashing dan caching ada di utils.py)
    cache_path = utils.generate_thumbnail(abs_path)

    if cache_path and os.path.exists(cache_path):
        # 3. Kirim Thumbnail yang Sudah Dicache (Selalu JPEG/image/jpeg karena di-convert di utils)
        return send_file(cache_path, mimetype='image/jpeg')
    else:
        # Jika gagal atau bukan file gambar, kembalikan 404 (Ini akan memicu fallback ikon di frontend)
        return "Thumbnail generation failed or file is not an image.", 404
