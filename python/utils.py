# utils.py

import os, sys, math, shutil, socket, time, subprocess, signal, re, requests
from . import config # Import konfigurasi dari file config.py

# --- FILE & DISK UTILITIES ---

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

def _is_within_root(path):
    try:
        return os.path.commonpath([os.path.realpath(config.ROOT_PATH), os.path.realpath(path)]) == os.path.realpath(config.ROOT_PATH)
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

def list_dir(path):
    files=[]
    try:
        # Pengecekan path yang lebih aman
        try: abs_path=os.path.abspath(path)
        except: abs_path=config.ROOT_PATH
        if not _is_within_root(abs_path) or not os.path.exists(abs_path): abs_path=config.ROOT_PATH
        
        if not os.path.exists(abs_path): return files
        # Sortir: Folder dulu, lalu file, alfabet case-insensitive
        for name in sorted(os.listdir(abs_path), key=lambda n: (not os.path.isdir(os.path.join(abs_path, n)), n.lower())):
            full_path = os.path.join(abs_path, name)
            # Cek symlink agar tidak keluar dari root
            if os.path.islink(full_path) and not _is_within_root(full_path): continue
            
            is_dir = os.path.isdir(full_path)
            size_bytes, size_formatted, icon_class = 0,"","fa-file"
            
            if is_dir:
                # Ukuran direktori
                size_bytes = get_directory_size(full_path)
                size_formatted = format_size(size_bytes) if size_bytes>=0 else "Error"
                icon_class = "fa-folder"
            else:
                # Ukuran file
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


# --- DNS CHECK HELPERS (DOH) ---

def doh_resolves(hostname, timeout=5):
    urls = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A",
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=AAAA",
        f"https://dns.google/resolve?name={hostname}&type=AAAA"
    ]
    headers = {"Accept":"application/dns-json"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=timeout)
            if r.status_code == 200:
                try:
                    j = r.json()
                    # Status 0 berarti DNS query sukses, dan Answer array tidak kosong berarti ada record A/AAAA
                    if j.get("Status") == 0 and j.get("Answer"):
                        return True
                except Exception: continue
        except Exception: continue
    try:
        # Fallback ke resolver sistem/socket default
        socket.getaddrinfo(hostname, None)
        return True
    except Exception:
        return False
        
# --- CLOUDFLARE UTILITIES ---

def ensure_cloudflared():
    if os.path.exists(config.CLOUDFLARED_BIN) and os.access(config.CLOUDFLARED_BIN, os.X_OK): return True
    try:
        print("Mengunduh cloudflared...")
        # Gunakan os.system/subprocess.run daripada subprocess.Popen untuk unduh
        rc = subprocess.run(f"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O {config.CLOUDFLARED_BIN}", shell=True).returncode
        if rc!=0:
             rc = subprocess.run(f"curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o {config.CLOUDFLARED_BIN}", shell=True).returncode
        if rc==0:
            os.chmod(config.CLOUDFLARED_BIN,0o755)
            return True
        else:
            print("Gagal unduh cloudflared setelah mencoba wget dan curl.")
            return False
    except Exception as e:
        print("Gagal unduh cloudflared:", e)
        return False

def start_cloudflared(proc_args):
    try:
        # Menggunakan os.setsid untuk membuat proses baru agar mudah di-kill grupnya
        proc = subprocess.Popen(proc_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid)
        return proc
    except Exception as e:
        print("Gagal start cloudflared:", e)
        return None

def stop_proc(proc):
    try:
        if proc and proc.poll() is None:
            # Kirim SIGTERM ke seluruh grup proses
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(0.3)
            # Jika masih hidup, kirim SIGKILL
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
