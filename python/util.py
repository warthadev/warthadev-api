# util.py - versi lengkap untuk main.py / flaskapp.py
import os, math, shutil

# --- FORMAT SIZE ---
def format_size(size_bytes):
    if size_bytes is None or size_bytes < 0: return "0 B"
    if size_bytes == 0: return "0 B"
    size_name = ("B","KB","MB","GB","TB")
    i = int(math.floor(math.log(size_bytes,1024)))
    p = math.pow(1024,i)
    s = round(size_bytes/p,2)
    return f"{s} {size_name[i]}"

# --- GET DISK USAGE ---
def get_disk_usage(path):
    try:
        if not os.path.exists(path): return 0,0,0.0
        total, used, free = shutil.disk_usage(path)
        percent = (used/total)*100 if total>0 else 0.0
        return total, used, percent
    except: return 0,0,0.0

# --- CHECK PATH DALAM ROOT ---
def _is_within_root(path, ROOT_PATH="."):
    try:
        return os.path.commonpath([os.path.realpath(ROOT_PATH), os.path.realpath(path)]) == os.path.realpath(ROOT_PATH)
    except: return False

# --- GET DIRECTORY SIZE ---
def get_directory_size(start_path='.'):
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(start_path):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                except: continue
    except: return -1
    return total_size

# --- GET FILE ICON CLASS ---
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

# --- LIST DIRECTORY (folder dulu, file belakangan) ---
def list_dir(path, ROOT_PATH="."):
    files = []
    try:
        if not os.path.exists(path): 
            return files
        # Urutkan: folder dulu, file lalu, case-insensitive
        for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower())):
            full_path = os.path.join(path, name)
            if os.path.islink(full_path) and not _is_within_root(full_path, ROOT_PATH):
                continue
            is_dir = os.path.isdir(full_path)
            size_bytes = get_directory_size(full_path) if is_dir else os.path.getsize(full_path)
            size_formatted = format_size(size_bytes) if size_bytes >=0 else "Error"
            icon_class = "fa-folder" if is_dir else get_file_icon_class(name)
            files.append({
                "name": name,
                "full_path": full_path,
                "is_dir": is_dir,
                "size_bytes": size_bytes,
                "size": size_formatted,
                "icon_class": icon_class
            })
    except Exception as e:
        files.append({"name":f"ERROR: {e}", "is_dir":False, "full_path":"", "size":"", "icon_class":"fa-exclamation-triangle", "size_bytes":0})
    return files