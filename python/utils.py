# utils.py
import os, math, shutil, re, sys
import hashlib # BARIS BARU: Import hashlib untuk hashing file path
from PIL import Image, ImageOps # BARIS BARU: Import PIL untuk image processing

# --- KONSTANTA BARU ---
CACHE_ROOT = "/tmp/cache/image" # Direktori Cache
MAX_THUMBNAIL_SIZE = (1024, 1024) # Ukuran maksimum thumbnail sesuai permintaan
# ----------------------

# --- UTILITY FUNCTIONS ---
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

def _is_within_root(path, root_path):
    try:
        return os.path.commonpath([os.path.realpath(root_path), os.path.realpath(path)]) == os.path.realpath(root_path)
    except: return False

def get_directory_size(start_path='.'):
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(start_path):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                except:
                    continue
    except:
        return -1
    return total_size

# FUNGSI BARU: Mendapatkan Path Cache dan Hash
def _get_cache_path_info(full_path):
    """Menghitung hash dan mengembalikan path cache yang akan mempertahankan ekstensi file asli."""
    try:
        # Gunakan path file sebagai string unik untuk hashing
        path_bytes = os.path.realpath(full_path).encode('utf-8')
        # Gunakan path file sebagai string unik untuk hashing
        file_hash = hashlib.sha256(path_bytes).hexdigest()
        
        # Ekstrak nama file asli dan ekstensi
        # Mempertahankan ekstensi agar browser tahu tipe filenya saat diunduh
        _, ext = os.path.splitext(os.path.basename(full_path))
        ext = ext.lower()
        
        # Path cache: [file_hash].[ext]
        cache_file_name = f"{file_hash}{ext}"
        cache_path = os.path.join(CACHE_ROOT, cache_file_name)
        
        return cache_path, ext
    except Exception:
        return None, None

# FUNGSI BARU: Mengambil/Membuat Thumbnail Terkompresi
def get_image_thumbnail(full_path):
    """Membuat thumbnail berukuran 1024x1024, menyimpannya ke cache, dan mengembalikan path cache."""
    cache_path, ext = _get_cache_path_info(full_path)
    if not cache_path: return None

    # 1. Cek Cache
    # Jika file cache sudah ada DAN lebih baru dari file asli (agar thumbnail file yang diedit dibuat ulang)
    if os.path.exists(cache_path) and os.path.getmtime(cache_path) >= os.path.getmtime(full_path):
        return cache_path

    # 2. Jika Cache hilang/basi, buat ulang
    try:
        os.makedirs(CACHE_ROOT, exist_ok=True)
        
        # Muat gambar
        img = Image.open(full_path)
        
        # Konversi ke RGB jika mode bukan (untuk menghindari masalah saat menyimpan JPEG)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        # Terapkan orientasi EXIF (penting agar gambar tidak terbalik)
        img = ImageOps.exif_transpose(img)
        
        # Ubah ukuran menjadi 1024x1024 (maksimum)
        img.thumbnail(MAX_THUMBNAIL_SIZE)
        
        # Tentukan format penyimpanan (default JPEG dengan kompresi)
        save_format = 'JPEG'
        quality = 75
        
        if ext in ['.png']: 
            save_format = 'PNG' 
            quality = 0 # PNG tidak menggunakan kualitas, tapi dapat dioptimalkan
        elif ext in ['.webp']:
            save_format = 'WEBP'
            quality = 75
        
        img.save(cache_path, format=save_format, quality=quality, optimize=True)
        
        return cache_path
        
    except Exception:
        # Gagal membuat thumbnail (misal: file gambar rusak atau format tidak didukung)
        return None 

# FUNGSI ASLI: Mengambil Kelas Ikon
def get_file_icon_class(name):
    # DARI KODE ASLI ANDA
    ext = os.path.splitext(name)[1].lower()
    
    # Pemetaan Ikon. Tambahkan/Perbarui untuk mencakup semua ekstensi yang dikenal.
    ICON_MAPPING = {
        # Gambar
        '.jpg': 'fa-image', '.jpeg': 'fa-image', '.png': 'fa-image', '.gif': 'fa-image', '.webp': 'fa-image',
        # Video
        '.mp4': 'fa-video', '.mkv': 'fa-video', '.avi': 'fa-video', '.mov': 'fa-video',
        # Audio
        '.mp3': 'fa-music', '.wav': 'fa-music', '.flac': 'fa-music',
        # Dokumen
        '.pdf': 'fa-file-pdf', '.doc': 'fa-file-word', '.docx': 'fa-file-word',
        '.xls': 'fa-file-excel', '.xlsx': 'fa-file-excel',
        '.ppt': 'fa-file-powerpoint', '.pptx': 'fa-file-powerpoint',
        # Kode & Teks
        '.py': 'fa-file-code', '.js': 'fa-file-code', '.html': 'fa-file-code',
        '.css': 'fa-file-code', '.json': 'fa-file-code', '.xml': 'fa-file-code',
        '.txt': 'fa-file-alt', '.md': 'fa-file-alt', 
        # Kompresi
        '.zip': 'fa-file-archive', '.rar': 'fa-file-archive', '.7z': 'fa-file-archive', '.tar.gz': 'fa-file-archive',
    }
    
    # Ikon 'fa-image' adalah kunci untuk memicu logika thumbnail di views.py/main.html
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
        return 'fa-image' 
        
    return ICON_MAPPING.get(ext, 'fa-file')


def list_dir(path, root_path):
    files=[]
    try:
        if not os.path.exists(path): return files
        # Sortir: Folder dulu, lalu file, case-insensitive
        for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower())):
            full_path = os.path.join(path, name)
            # Cek keamanan symlink
            if os.path.islink(full_path) and not _is_within_root(full_path, root_path): continue
            
            is_dir = os.path.isdir(full_path)
            size_bytes, size_formatted, icon_class = 0,"","fa-file"
            
            # --- PENAMBAHAN UNTUK THUMBNAIL ---
            thumbnail_url = None
            is_image = False
            # ---------------------------------
            
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

                    # Jika file adalah gambar, set is_image=True dan thumbnail_url
                    if icon_class == 'fa-image':
                        is_image = True
                        # URL thumbnail menunjuk ke route Flask baru
                        thumbnail_url = f"/thumb?path={full_path}" 

                except: size_formatted="Error"
                
            files.append({
                "name": name, "is_dir": is_dir, "full_path": full_path,
                "size": size_formatted, "size_bytes": size_bytes, "icon_class": icon_class,
                "thumbnail_url": thumbnail_url, # BARIS BARU
                "is_image": is_image # BARIS BARU
            })
    
    except Exception as e:
        # print(f"Error listing directory {path}: {e}")
        pass

    return files
