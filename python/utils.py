# utils.py
import os, math, shutil, re, sys
# BARU: Impor untuk Thumbnailing
from PIL import Image 
import hashlib 

# Variabel yang akan disuntikkan dari app.py (HARAP TIDAK DIHAPUS)
ROOT_PATH = "/content" 
THUMBNAIL_CACHE_PATH = os.path.join(os.path.abspath("/tmp"), "thumbs") 
THUMBNAIL_SIZE = (1024, 1024) 

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
        # Menggunakan realpath untuk mengatasi symlink
        return os.path.commonpath([os.path.realpath(root_path), os.path.realpath(path)]) == os.path.realpath(root_path)
    except: return False

def get_directory_size(start_path='.'):
    # Fungsi ini sangat lambat dan disarankan tidak dipanggil saat list_dir
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(start_path):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    if not os.path.islink(fp): # Hindari menghitung symlink
                        total_size += os.path.getsize(fp)
                except Exception:
                    # File mungkin hilang/izin ditolak
                    pass
        return total_size
    except Exception:
        return -1 # Tanda error

def get_file_icon_class(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']: return "fas fa-file-archive"
    elif ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']: return "fas fa-video"
    elif ext in ['.mp3', '.wav', '.ogg', '.flac']: return "fas fa-file-audio"
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.ico', '.bmp', '.svg']: return "fas fa-image"
    elif ext in ['.pdf']: return "fas fa-file-pdf"
    elif ext in ['.doc', '.docx']: return "fas fa-file-word"
    elif ext in ['.xls', '.xlsx']: return "fas fa-file-excel"
    elif ext in ['.ppt', '.pptx']: return "fas fa-file-powerpoint"
    elif ext in ['.txt', '.log', '.md']: return "fas fa-file-alt"
    elif ext in ['.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.sh', '.c', '.cpp', '.h', '.java']: return "fas fa-file-code"
    return "fas fa-file"

# --- FUNGSI BARU: THUMBNAIL CACHING ---
def generate_thumbnail(file_path):
    """Membuat atau mengambil thumbnail dari cache."""
    
    # 1. Tentukan Nama File Cache
    try:
        # Gunakan hash path dan waktu modifikasi (mtime) untuk keunikan dan invalidasi
        mtime = str(os.path.getmtime(file_path))
        hash_name = hashlib.md5(f"{file_path}_{mtime}".encode()).hexdigest()
        
        # Simpan dalam format JPEG yang efisien
        cache_file_name = f"{hash_name}.jpg" 
        cache_path = os.path.join(THUMBNAIL_CACHE_PATH, cache_file_name)
    except Exception as e:
        print(f"Error hashing path {file_path}: {e}")
        return None

    # 2. Cek Cache
    if os.path.exists(cache_path):
        return cache_path # Thumbnail sudah ada dan valid

    # 3. Buat Thumbnail
    try:
        # Pastikan direktori cache ada
        os.makedirs(THUMBNAIL_CACHE_PATH, exist_ok=True)
        
        with Image.open(file_path) as img:
            # Mengubah ukuran gambar (resize)
            img.thumbnail(THUMBNAIL_SIZE) 
            
            # Simpan dengan kualitas yang baik ke cache
            img.save(cache_path, "JPEG", quality=85) 
            
        # print(f"✅ Thumbnail dibuat: {cache_path}")
        return cache_path
    except Exception as e:
        # Gagal membuat thumbnail (mungkin bukan file gambar yang valid atau izin)
        # print(f"❌ Gagal membuat thumbnail untuk {file_path}: {e}")
        # Hapus file cache yang gagal jika ada (parsial)
        if os.path.exists(cache_path): os.remove(cache_path)
        return None
        
# --- LIST DIR (FUNGSI UTAMA) ---
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
            
            if is_dir:
                # PERBAIKAN: Jangan hitung ukuran folder di list_dir untuk performa
                size_formatted = "-" 
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
