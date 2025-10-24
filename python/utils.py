import os, math, shutil

def format_size(size_bytes):
    if size_bytes <= 0: return "0 B"
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

def get_directory_size(start_path='.'):
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for fname in filenames:
            fp = os.path.join(dirpath, fname)
            try:
                if not os.path.islink(fp): total_size += os.path.getsize(fp)
            except: continue
    return total_size

def get_file_icon_class(filename):
    ext = os.path.splitext(filename)[1].lower()
    mapping = {
        "video": ['.mp4','.mkv','.avi','.mov','.wmv'],
        "audio": ['.mp3','.wav','.flac','.ogg'],
        "image": ['.jpg','.jpeg','.png','.gif','.bmp','.svg','.webp'],
        "code":  ['.py','.java','.c','.cpp','.html','.css','.js','.json','.xml','.sh'],
        "archive": ['.zip','.rar','.7z','.tar','.gz','.tgz'],
        "doc": ['.pdf','.doc','.docx'],
        "sheet": ['.xls','.xlsx','.csv'],
        "slide": ['.ppt','.pptx'],
        "text": ['.txt','.log','.md','.ini','.cfg','.yml','.yaml']
    }
    for k,v in mapping.items():
        if ext in v:
            return f"fa-file-{k}"
    return "fa-file"