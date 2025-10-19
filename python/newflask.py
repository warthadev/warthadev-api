# newflask.py (Untuk di-push ke GitHub)

import os, subprocess, re, time
from flask import Flask, render_template, send_file, request
from threading import Thread
from werkzeug.serving import run_simple 
import logging
import math
import shutil

# Nonaktifkan logging Flask/Werkzeug yang tidak perlu
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# --- KONFIGURASI GLOBAL (DI-INJECT) ---
ROOT_PATH = "/content" 
PORT = 8000
DECRYPTION_SUCCESS = False 
FIREBASE_CONFIG = None
CLOUDFLARE_CONFIG = None
PEM_BYTES = None

# Tambahkan path ke folder HTML di repo yang dikloning
# Asumsi: Repo dikloning ke /tmp/warthadev-api
TEMPLATE_FOLDER = os.path.join("/tmp/warthadev-api", "html")

# --- UTILITY FUNCTIONS ---

def format_size(size_bytes):
    """Mengubah byte menjadi format yang mudah dibaca (KB, MB, GB)."""
    if size_bytes <= 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_disk_usage(path):
    """Mendapatkan statistik penggunaan disk (total, used, percent)."""
    if not os.path.exists(path):
        return 0, 0, 0.0
    
    try:
        total, used, free = shutil.disk_usage(path)
        percent = (used / total) * 100 if total > 0 else 0
        return total, used, percent
    except Exception:
        return 0, 0, 0.0

def get_directory_size(start_path='.'):
    """Menghitung total ukuran semua file di dalam direktori secara rekursif."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Lewati symbolic link (untuk menghindari loop tak terbatas)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except Exception as e:
        # Jika ada error izin atau link rusak
        return -1 # Mengembalikan nilai negatif untuk menandakan error
    return total_size

def list_dir(path):
    """Mendaftar file dan folder dengan informasi ukuran (termasuk ukuran folder)."""
    files = []
    try:
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            
            # Cek apakah itu symbolic link yang mengarah ke luar root
            if os.path.islink(full_path) and not os.path.realpath(full_path).startswith(ROOT_PATH):
                continue
                
            is_dir = os.path.isdir(full_path)
            size_bytes = 0

            if is_dir:
                # HITUNG UKURAN FOLDER SECARA REKURSIF
                size_bytes = get_directory_size(full_path)
                size_formatted = format_size(size_bytes) if size_bytes >= 0 else "Error"
            else:
                # UKURAN FILE NORMAL
                stat = os.stat(full_path)
                size_bytes = stat.st_size
                size_formatted = format_size(size_bytes)

            files.append({
                "name": f,
                "is_dir": is_dir,
                "full_path": full_path,
                "size": size_formatted,
                "size_bytes": size_bytes
            })
    except Exception as e:
        print(f"list_dir error: {e}") 
        files.append({"name": f"ERROR: {e}", "is_dir": False, "full_path": "", "size": ""})

    # Hapus logika penambahan tombol '..'
    # Navigasi kembali ditangani oleh fixed-footer

    # Sortir: Folder, File, berdasarkan nama
    return sorted(files, key=lambda x: (not x['is_dir'], x['name'].lower()))

# --- INISIALISASI FLASK ---
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
app.jinja_env.globals.update(format_size=format_size, os_path=os.path)

# --- ROUTES ---

@app.route('/')
def index():
    path = request.args.get('path', ROOT_PATH)
    path = os.path.abspath(path)
    
    if not path.startswith(ROOT_PATH) or not os.path.exists(path):
        path = ROOT_PATH

    # Statistik Disk (Colab FS)
    colab_total, colab_used, colab_percent = get_disk_usage(ROOT_PATH)
    
    # Statistik Disk Drive (Asumsi Drive di-mount di /content/drive)
    drive_mount_path = "/content/drive"
    drive_total, drive_used, drive_percent = get_disk_usage(drive_mount_path)

    # List files
    all_files = list_dir(path)
    
    return render_template(
        'main.html',
        path=path,
        root_path=ROOT_PATH,
        files=all_files,
        colab_total=colab_total,
        colab_used=colab_used,
        colab_percent=colab_percent,
        drive_total=drive_total,
        drive_used=drive_used,
        drive_percent=drive_percent,
        drive_mount_path=drive_mount_path,
        DECRYPTION_SUCCESS=DECRYPTION_SUCCESS
    )

@app.route('/file')
def open_file():
    path = request.args.get('path')
    path = os.path.abspath(path)
    if not path.startswith(ROOT_PATH) or not os.path.isfile(path):
        return "File tidak bisa dibuka.", 404
    
    ext = os.path.splitext(path)[1].lower()
    
    if ext in ['.txt','.py','.csv','.md','.log','.json','.yml','.html','.css','.js']:
        try:
            with open(path,"r",encoding="utf-8",errors='ignore') as f:
                return f"<pre>{f.read()}</pre>"
        except Exception as e:
            return f"Gagal membaca file. ({e})", 500
    else:
        return send_file(path, as_attachment=True)


# --- FUNGSI PELUNCURAN UTAMA ---

def run_flask_and_tunnel():
    
    def run_flask():
        try:
            run_simple('0.0.0.0', PORT, app, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"Flask execution error: {e}")

    Thread(target=run_flask, daemon=True).start()

    # Log minimalis untuk cloudflared
    os.system('wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared-linux-amd64')
    os.system('chmod +x cloudflared-linux-amd64')

    proc = subprocess.Popen(
        ["./cloudflared-linux-amd64", "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    public_url = None
    for _ in range(30):
        line = proc.stdout.readline()
        if line:
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
            if m:
                public_url = m.group(1)
                break
        time.sleep(1)
        
    if public_url:
        print(public_url)
    else:
        print("Gagal mendapatkan URL Cloudflare.")
