# python/flask.py (Versi Diperbaiki)

# Pastikan semua modul yang digunakan diimpor di sini.
import os, shutil, importlib.util, json, stat # <--- FIX: Tambahkan os dan stat
from threading import Thread
from flask import Flask, jsonify, request, render_template, redirect, url_for
from pyngrok import ngrok
import logging
from firebase_admin import firestore
import os.path as os_path # <--- FIX: os.path diimpor untuk digunakan di Jinja2

# --- CONFIG ---
ROOT_PATH = "/content"
DRIVE_MOUNT_PATH = "/content/drive"
PORT = 5000 # <--- FIX: Pastikan ini berada di level atas

# STATE global (akan diinisialisasi dari skrip Colab utama)
STATE = {"tunnel_url": None, "tunnel_token": None, "db": None}

# Menonaktifkan logging Flask default
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- FUNGSI PEMBANTU (Menggunakan os yang sudah diimpor) ---

def format_size(size_bytes):
    # ... (tetap sama)
    if size_bytes < 1024: return f"{size_bytes} B"
    size_bytes /= 1024
    if size_bytes < 1024: return f"{size_bytes:.1f} KB"
    size_bytes /= 1024
    if size_bytes < 1024: return f"{size_bytes:.1f} MB"
    size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

def get_dir_size(start_path='.'):
    # ... (tetap sama, menggunakan os.scandir dan os.stat)
    total_size = 0
    try:
        for entry in os.scandir(start_path):
            if entry.is_file(): total_size += entry.stat().st_size
            elif entry.is_dir() and not entry.is_symlink(): total_size += get_dir_size(entry.path)
    except Exception: pass
    return total_size

def get_disk_usage(path):
    # ... (tetap sama, menggunakan os.statvfs)
    try:
        statvfs = os.statvfs(path)
        total = statvfs.f_blocks * statvfs.f_frsize
        free = statvfs.f_bfree * statvfs.f_frsize
        used = total - free
        percent_used = (used / total) * 100 if total > 0 else 0
        return total, used, free, percent_used
    except Exception:
        return 0, 0, 0, 0

def list_dir(path):
    # ... (tetap sama, menggunakan os.listdir, os.path.join, os.stat)
    files = []
    try:
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            if path == DRIVE_MOUNT_PATH and f == ".shortcut-targets-by-id": continue
            try:
                file_stat = os.stat(full_path)
                is_dir = stat.S_ISDIR(file_stat.st_mode)

                size_bytes = get_dir_size(full_path) if is_dir else file_stat.st_size
                size_formatted = format_size(size_bytes)

                files.append({"name": f, "is_dir": is_dir, "full_path": full_path, "size": size_formatted})
            except Exception:
                files.append({"name": f, "is_dir": os.path.isdir(full_path), "full_path": full_path, "size": "N/A"})
    except PermissionError: pass
    except FileNotFoundError: pass

    seen_names = set()
    unique_files = []
    for f in files:
        if f['name'] not in seen_names:
            unique_files.append(f)
            seen_names.add(f['name'])

    return sorted(unique_files, key=lambda x: (not x['is_dir'], x['name'].lower()))


# --- INISIALISASI FLASK APP & RUNTIME ---

# Mendefinisikan jalur ke folder template: "../html" relatif terhadap python/
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html")

app = Flask(__name__, template_folder=template_dir) # Mengatur lokasi template


@app.route("/")
def index():
    path = request.args.get('path', ROOT_PATH)
    path = os.path.abspath(path)

    if not path.startswith(ROOT_PATH) or not os.path.exists(path): path = ROOT_PATH
    if path == DRIVE_MOUNT_PATH and os.path.exists(os.path.join(path, "MyDrive")): path = os.path.join(path, "MyDrive")

    all_files = list_dir(path)
    
    colab_total, colab_used, _, colab_percent = get_disk_usage(ROOT_PATH)
    drive_total, drive_used, _, drive_percent = get_disk_usage(DRIVE_MOUNT_PATH) if os.path.exists(DRIVE_MOUNT_PATH) else (0, 0, 0, 0)

    # Menggunakan render_template dan mengirim semua data yang diperlukan
    return render_template(
        "main.html",
        path=path,
        files=all_files,
        # Data Disk
        colab_total=colab_total,
        colab_used=colab_used,
        colab_percent=colab_percent,
        drive_total=drive_total,
        drive_used=drive_used,
        drive_percent=drive_percent,
        # Fungsi dan Konstanta untuk Jinja2
        format_size=format_size,
        root_path=ROOT_PATH,
        drive_mount_path=DRIVE_MOUNT_PATH,
        os_path=os_path
    )

@app.route("/set_tunnel")
def set_tunnel():
    # ... (tetap sama)
    token = request.args.get("token", default=None, type=str)
    if not token: return jsonify({"ok": False, "msg": "Missing token param. Gunakan ?token=PASTE_TOKEN"}), 400

    try:
        ngrok.set_auth_token(token)
        ngrok.kill()
        public_url = ngrok.connect(PORT).public_url
        STATE["tunnel_url"] = public_url
        STATE["tunnel_token"] = token

        db = STATE.get("db")
        if db:
            DOC_COL = "tunnel"
            DOC_ID = "token"
            doc_ref = db.collection(DOC_COL).document(DOC_ID)
            from firebase_admin import firestore # Harus diimpor di sini jika tidak diimpor di global scope
            doc_ref.set({"tunnel": token, "ngrok": token, "_tunnel_saved_at": firestore.SERVER_TIMESTAMP}, merge=True)

        return jsonify({"ok": True, "msg": "Tunnel started", "public_url": public_url})
    except Exception as e:
        return jsonify({"ok": False, "msg": "Failed to start tunnel: " + str(e)}), 500

@app.route("/status")
def status():
    return jsonify({"ok": True, "tunnel_url": STATE.get("tunnel_url"), "tunnel_token_present": True if STATE.get("tunnel_token") else False, "flask_running": True})

# Fungsi utama yang dipanggil dari skrip Colab
def run_flask(db_client, initial_token):
    STATE["db"] = db_client
    STATE["tunnel_token"] = initial_token

    thread = Thread(target=lambda: app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False), daemon=True)
    thread.start()

    public_url = None
    if STATE.get("tunnel_token"):
        try:
            ngrok.set_auth_token(STATE["tunnel_token"])
            public_url = ngrok.connect(PORT).public_url
            STATE["tunnel_url"] = public_url
            # print("✅ Tunnel auto-start berhasil!")
        except Exception as e:
            pass
            # print(f"⚠️ Gagal auto-start tunnel: {e}. Coba set token secara manual.")

    return public_url
