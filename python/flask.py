# python/flask.py (Versi Diperbarui dan Final untuk Cloudflare)

import os, shutil, importlib.util, json, stat, sys, subprocess
from threading import Thread
from flask import Flask, jsonify, request, render_template, redirect, url_for
import logging
from firebase_admin import firestore
import os.path as os_path
import time 

# Import Pyrogram secara tentatif
try:
    import pyrogram
except ImportError:
    pyrogram = None # Akan diset None jika belum terinstal

# --- CONFIG ---
ROOT_PATH = "/content"
DRIVE_MOUNT_PATH = "/content/drive"
TELEGRAM_TOKEN_PATH = os.path.join(DRIVE_MOUNT_PATH, "warthadev-token.json")
PORT = 5000

# STATE global 
STATE = {"db": None, "login_status": None} # Menghapus 'tunnel_url' dan 'tunnel_token'

# --- FUNGSI PEMBANTU (Tidak Berubah) ---

def format_size(size_bytes):
    if size_bytes < 1024: return f"{size_bytes} B"
    size_bytes /= 1024
    if size_bytes < 1024: return f"{size_bytes:.1f} KB"
    size_bytes /= 1024
    if size_bytes < 1024: return f"{size_bytes:.1f} MB"
    size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

def get_dir_size(start_path='.'):
    total_size = 0
    try:
        for entry in os.scandir(start_path):
            if entry.is_file(): total_size += entry.stat().st_size
            elif entry.is_dir() and not entry.is_symlink(): total_size += get_dir_size(entry.path)
    except Exception: pass
    return total_size

def get_disk_usage(path):
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

# --- FUNGSI BARU UNTUK TELEGRAM (Sedikit Modifikasi untuk kejelasan) ---

def install_pyrogram_if_needed():
    """Menginstal Pyrogram jika belum tersedia."""
    global pyrogram
    if pyrogram is None:
        try:
            print("🚀 Memulai instalasi Pyrogram...")
            # Menggunakan subprocess.check_call untuk menjalankan pip install
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyrogram"])
            # Coba impor lagi
            import pyrogram
            print("✅ Pyrogram berhasil diinstal.")
            # Set variabel global pyrogram setelah instalasi
            globals()['pyrogram'] = pyrogram
            return True
        except Exception as e:
            print(f"❌ Gagal menginstal Pyrogram: {e}")
            return False
    return True # Sudah terinstal

def get_telegram_credentials():
    """Mengambil api_id dan api_hash dari Firestore."""
    db = STATE.get("db")
    if not db:
        return None, None
    try:
        DOC_COL = "api" 
        DOC_ID = "token"
        doc_ref = db.collection(DOC_COL).document(DOC_ID)
        doc_snap = doc_ref.get()
        doc_data = doc_snap.to_dict() if doc_snap.exists else {}
        
        api_id = doc_data.get("telegram-api-id")
        api_hash = doc_data.get("telegram-api-hash") 
        
        # Fallback untuk bug 'telegram-api-hast'
        if not api_hash:
             api_hash = doc_data.get("telegram-api-hast")
        
        if api_id:
            try: api_id = int(api_id)
            except ValueError: return None, None 

        return api_id, api_hash
    except Exception as e:
        print(f"❌ Gagal mengambil kredensial Telegram dari Firestore: {e}")
        return None, None

def pyrogram_login_thread(api_id, api_hash):
    """Fungsi yang berjalan di thread terpisah untuk login interaktif Pyrogram."""
    global pyrogram
    session_name = "colab_warthadev_session"
    
    print("\n" + "="*50)
    print("🤖 MEMULAI LOGIN INTERAKTIF PYROGRAM")
    print("   Harap cek log Colab untuk prompt input (Nomor/OTP/2FA)")
    print("="*50)
    
    app_client = pyrogram.Client(
        session_name,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True 
    )

    STATE["login_status"] = "PROMPT_USER_INPUT" 
    
    try:
        app_client.start()
        
        session_string = app_client.export_session_string()
        
        # SIMPAN session string ke Drive
        data_to_save = {
            "session_string": session_string,
            "api_id": api_id,
            "api_hash": api_hash
        }
        with open(TELEGRAM_TOKEN_PATH, 'w') as f:
            json.dump(data_to_save, f)
        
        print("\n" + "="*50)
        print("✅ Session String berhasil dibuat dan disimpan ke Drive.")
        print(f"   PATH: {TELEGRAM_TOKEN_PATH}")
        print("="*50)
        
        STATE["login_status"] = "SUCCESS"

    except Exception as e:
        print(f"\n❌ GAGAL LOGIN PYROGRAM: {e}")
        STATE["login_status"] = f"FAILED: {str(e)}"
        
    finally:
        try:
            app_client.stop()
        except Exception:
            pass
        
# --- INISIALISASI FLASK APP & ROUTE ---

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html")
app = Flask(__name__, template_folder=template_dir)


@app.route("/")
def index():
    path = request.args.get('path', ROOT_PATH)
    path = os.path.abspath(path)

    if not path.startswith(ROOT_PATH) or not os.path.exists(path): path = ROOT_PATH
    if path == DRIVE_MOUNT_PATH and os.path.exists(os.path.join(path, "MyDrive")): path = os.path.join(path, "MyDrive")

    all_files = list_dir(path)
    
    colab_total, colab_used, _, colab_percent = get_disk_usage(ROOT_PATH)
    drive_total, drive_used, _, drive_percent = get_disk_usage(DRIVE_MOUNT_PATH) if os.path.exists(DRIVE_MOUNT_PATH) else (0, 0, 0, 0)

    return render_template(
        "main.html",
        path=path,
        files=all_files,
        colab_total=colab_total,
        colab_used=colab_used,
        colab_percent=colab_percent,
        drive_total=drive_total,
        drive_used=drive_used,
        drive_percent=drive_percent,
        format_size=format_size,
        root_path=ROOT_PATH,
        drive_mount_path=DRIVE_MOUNT_PATH,
        os_path=os_path
    )

# MENGHAPUS @app.route("/set_tunnel") (Telah dihapus karena berbasis Ngrok)

@app.route("/status")
def status():
    # Menghapus 'tunnel_url' dan 'tunnel_token_present' karena ditentukan oleh skrip Colab utama
    return jsonify({"ok": True, "flask_running": True, "login_status": STATE.get("login_status")})

# --- ROUTE TELEGRAM (Tidak Berubah) ---

@app.route("/telegram/config")
def telegram_config():
    is_pyrogram_installed = install_pyrogram_if_needed()
    api_id, api_hash = get_telegram_credentials()
    is_session_saved = os.path.exists(TELEGRAM_TOKEN_PATH)

    return render_template(
        "tele-config.html", 
        is_pyrogram_installed=is_pyrogram_installed,
        api_id=api_id,
        api_hash=api_hash,
        is_session_saved=is_session_saved,
        telegram_token_path=TELEGRAM_TOKEN_PATH,
        login_status=STATE.get("login_status") 
    )

@app.route("/telegram/get_session")
def get_session():
    if pyrogram is None:
        return jsonify({"ok": False, "msg": "Pyrogram belum terinstal atau gagal diimpor."}), 500

    api_id, api_hash = get_telegram_credentials()

    if not api_id or not api_hash:
        return jsonify({"ok": False, "msg": "Telegram API ID atau Hash tidak ditemukan di Firestore."}), 400
    
    if STATE.get("login_status") == "PROMPT_USER_INPUT":
         return jsonify({"ok": False, "msg": "Proses login sudah berjalan. Cek log Colab Anda!"}), 409
         
    thread = Thread(target=pyrogram_login_thread, args=(api_id, api_hash,), daemon=True)
    thread.start()
    
    time.sleep(1)

    return jsonify({
        "ok": True, 
        "msg": "Login interaktif dimulai! Cek log Colab untuk memasukkan nomor telepon, OTP, dan 2FA Anda."
    })

@app.route("/telegram/set_session", methods=['POST'])
def set_session():
    session_string = request.form.get("session_string")
    if not session_string:
        return jsonify({"ok": False, "msg": "Session string tidak boleh kosong."}), 400
        
    api_id, api_hash = get_telegram_credentials()

    if not api_id or not api_hash:
        return jsonify({"ok": False, "msg": "Telegram API ID atau Hash tidak ditemukan di Firestore."}), 400
        
    try:
        if not session_string.startswith("BQ"):
             return jsonify({"ok": False, "msg": "Session string Pyrogram tidak valid (harus diawali 'BQ')."}), 400
             
        data_to_save = {
            "session_string": session_string,
            "api_id": api_id,
            "api_hash": api_hash
        }
        with open(TELEGRAM_TOKEN_PATH, 'w') as f:
            json.dump(data_to_save, f)

        return jsonify({"ok": True, "msg": "Session String berhasil disimpan ke Drive.", "path": TELEGRAM_TOKEN_PATH})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Gagal menyimpan session: {e}"}), 500


# --- FUNGSI UTAMA RUNTIME (FINAL) ---

def run_flask(db_client, initial_token):
    """
    Menjalankan server Flask secara lokal.
    initial_token (dari Firestore) diabaikan di sini karena tunneling dilakukan oleh Cloudflare.
    """
    STATE["db"] = db_client
    # STATE['tunnel_token'] tidak lagi diperlukan/digunakan

    # Atur level log tepat sebelum server dimulai
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # Hanya menjalankan Flask lokal di port 5000 di thread terpisah
    thread = Thread(target=lambda: app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False), daemon=True)
    thread.start()

    # TIDAK MENGEMBALIKAN URL PUBLIK KARENA TUNNELING DILAKUKAN DI SCRIPT UTAMA
    return True
