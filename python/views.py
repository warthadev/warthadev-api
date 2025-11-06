# views.py
import os, sys
from flask import render_template, send_file, request, jsonify
import utils 

# Variabel yang akan disuntikkan dari app.py
ROOT_PATH = "/content"
DECRYPTION_SUCCESS = False
TEMPLATE_FOLDER = ""
app = None 


def index():
    """Route utama untuk menampilkan file manager."""
    if app is None or TEMPLATE_FOLDER == "": return "Server not fully initialized.", 500

    req_path = request.args.get("path", ROOT_PATH)
    try: abs_path=os.path.abspath(req_path)
    except: abs_path=ROOT_PATH
    
    # Keamanan: Pastikan path berada di dalam ROOT_PATH
    if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path): abs_path=ROOT_PATH
    
    colab_total, colab_used, colab_percent = utils.get_disk_usage(ROOT_PATH)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = utils.get_disk_usage(drive_mount_path)
    
    files = utils.list_dir(abs_path, ROOT_PATH)
    tpl = "main.html"
    
    # Logika fallback (HTML mentah)
    if not os.path.exists(os.path.join(TEMPLATE_FOLDER, tpl)):
        items_html = "\n".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
        return f"<html><body><h3>{abs_path}</h3>{items_html}</body></html>" 
        
    # KODE INI DIPERBAIKI (MENGGUNAKAN TANDA KURUNG BUKAN \)
    return render_template(tpl, 
        path=abs_path, 
        root_path=ROOT_PATH, 
        files=files,
        colab_total=colab_total, 
        colab_used=colab_used, 
        colab_percent=colab_percent,
        drive_total=drive_total, 
        drive_used=drive_used, 
        drive_percent=drive_percent,
        drive_mount_path=drive_mount_path,
        # Perluas filter jinja2 untuk format size di HTML
        format_size=utils.format_size
    )


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
        # Tampilkan konten teks (asumsi template view_text ada)
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024*1024) # Batasi 1MB untuk ditampilkan
            return render_template('view_text.html', path=abs_path, content=content)
        except Exception:
            # Fallback ke download jika error membaca/menampilkan
            pass
            
    # Default: Unduh File
    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))
    
# FUNGSI BARU: Route untuk melayani Thumbnail
def serve_thumbnail():
    """Route untuk mendapatkan thumbnail yang di-cache dari gambar asli."""
    original_path = request.args.get("path", "")
    if not original_path: 
        return "Path missing", 400
        
    try:
        # Cek keamanan: Pastikan file asli berada di dalam ROOT_PATH
        abs_path = os.path.abspath(original_path)
        if not utils._is_within_root(abs_path, ROOT_PATH) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            return "File cannot be processed (Security/404).", 404
            
        # Panggil fungsi caching dari utils
        cache_path = utils.get_image_thumbnail(abs_path)
        
        if cache_path and os.path.exists(cache_path):
            # Tentukan MIME type berdasarkan ekstensi file cache (yang mempertahankan ekstensi asli)
            ext = os.path.splitext(cache_path)[1].lower()
            mimetype = 'image/jpeg'
            if ext == '.png': mimetype = 'image/png'
            elif ext == '.webp': mimetype = 'image/webp'
            
            # Melayani file cache
            return send_file(cache_path, 
                             mimetype=mimetype,
                             max_age=31536000, # Cache selama 1 tahun (nama file adalah hash)
                             as_attachment=False)
        else:
            return "Thumbnail generation failed or is not an image.", 404

    except Exception:
        return "Internal Server Error during thumbnail service.", 500