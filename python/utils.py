import os, math, shutil

def format_size(size_bytes):
    if not size_bytes or size_bytes < 0: return "0 B"
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes/p, 2)
    return f"{s} {'B','KB','MB','GB','TB'[i]}"

def get_disk_usage(path):
    try:
        if not os.path.exists(path): return 0,0,0.0
        total, used, free = shutil.disk_usage(path)
        percent = (used/total)*100 if total>0 else 0.0
        return total, used, percent
    except: return 0,0,0.0

def _is_within_root(path, root):
    try:
        return os.path.commonpath([os.path.realpath(root), os.path.realpath(path)]) == os.path.realpath(root)
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
    video = ['.mp4','.mkv','.avi','.mov','.wmv']
    audio = ['.mp3','.wav','.flac','.ogg']
    image = ['.jpg','.jpeg','.png','.gif','.bmp','.svg','.webp']
    code = ['.py','.java','.c','.cpp','.html','.css','.js','.json','.xml','.sh']
    archive = ['.zip','.rar','.7z','.tar','.gz','.tgz']
    if ext in video: return "fa-file-video"
    if ext in audio: return "fa-file-audio"
    if ext in image: return "fa-file-image"
    if ext in code: return "fa-file-code"
    if ext in archive: return "fa-file-archive"
    return "fa-file"

def list_dir(path, root):
    files=[]
    if not os.path.exists(path): return files
    for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower())):
        full_path = os.path.join(path, name)
        if os.path.islink(full_path) and not _is_within_root(full_path, root): continue
        is_dir = os.path.isdir(full_path)
        size_bytes, size_formatted, icon_class = 0, "", "fa-file"
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
    return files