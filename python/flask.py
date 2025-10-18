# python/flask.py (Versi Diperbarui dan Final)

import os, shutil, importlib.util, json, stat, sys, subprocess
from threading import Thread
from flask import Flask, jsonify, request, render_template, redirect, url_for
from pyngrok import ngrok
import logging
from firebase_admin import firestore
import os.path as os_path
import time # Diperlukan untuk memberi jeda pada threading

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

# STATE global (akan diinisialisasi dari skrip Colab utama)
STATE = {"tunnel_url": None, "tunnel_token": None, "db": None, "login_status": None} # Menambah 'login_status'

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

# --- FUNGSI BARU UNTUK TELEGRAM ---

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
        # PERBAIKAN BUG: Mengganti 'telegram-api-hast' menjadi 'telegram-api-hash'
        api_hash = doc_data.get("telegram-api-hash") 
        
        # Jika 'telegram-api-hast' masih digunakan di database lama, pakai fallback
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
    # Nama sesi sementara yang tidak akan digunakan Pyrogram secara default
    session_name = "colab_warthadev_session"
    
    print("\n" + "="*50)
    print("🤖 MEMULAI LOGIN INTERAKTIF PYROGRAM")
    print("   Harap cek log Colab untuk prompt input (Nomor/OTP/2FA)")
    print("="*50)
    
    # Klien Pyrogram: 'in_memory' agar tidak membuat file sesi otomatis
    app_client = pyrogram.Client(
        session_name,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True 
    )

    STATE["login_status"] = "PROMPT_USER_INPUT" # Status: Menunggu input pengguna di log Colab
    
    try:
        app_client.start()
        
        # Ambil session string setelah login berhasil
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
        print("   Pastikan nomor, OTP, dan password 2FA yang dimasukkan benar.")
        STATE["login_status"] = f"FAILED: {str(e)}"
        
    finally:
        # Hentikan klien Pyrogram
        try:
            app_client.stop()
        except Exception:
            pass
        
# --- INISIALISASI FLASK APP & ROUTE (Tidak Berubah) ---

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
            # Impor firestore di sini untuk menghindari circular dependency
            from firebase_admin import firestore
            doc_ref.set({"tunnel": token, "ngrok": token, "_tunnel_saved_at": firestore.SERVER_TIMESTAMP}, merge=True)

        return jsonify({"ok": True, "msg": "Tunnel started", "public_url": public_url})
    except Exception as e:
        return jsonify({"ok": False, "msg": "Failed to start tunnel: " + str(e)}), 500

@app.route("/status")
def status():
    return jsonify({"ok": True, "tunnel_url": STATE.get("tunnel_url"), "tunnel_token_present": True if STATE.get("tunnel_token") else False, "flask_running": True})

# --- ROUTE TELEGRAM ---

@app.route("/telegram/config")
def telegram_config():
    # 1. Cek dan Instal Pyrogram
    is_pyrogram_installed = install_pyrogram_if_needed()
    
    # 2. Ambil kredensial Firestore
    api_id, api_hash = get_telegram_credentials()
    
    # 3. Cek apakah session string sudah ada di Drive
    is_session_saved = os.path.exists(TELEGRAM_TOKEN_PATH)

    return render_template(
        "tele-config.html", # Menggunakan nama file template yang benar
        is_pyrogram_installed=is_pyrogram_installed,
        api_id=api_id,
        api_hash=api_hash,
        is_session_saved=is_session_saved,
        telegram_token_path=TELEGRAM_TOKEN_PATH,
        # Tambahkan status login untuk feedback di front-end
        login_status=STATE.get("login_status") 
    )

@app.route("/telegram/get_session")
def get_session():
    # PENTING: Pyrogram harus terinstal dan diimpor.
    if pyrogram is None:
        return jsonify({"ok": False, "msg": "Pyrogram belum terinstal atau gagal diimpor."}), 500

    api_id, api_hash = get_telegram_credentials()

    if not api_id or not api_hash:
        return jsonify({"ok": False, "msg": "Telegram API ID atau Hash tidak ditemukan di Firestore."}), 400
    
    if STATE.get("login_status") == "PROMPT_USER_INPUT":
         return jsonify({"ok": False, "msg": "Proses login sudah berjalan. Cek log Colab Anda!"}), 409
         
    # Jalankan proses login Pyrogram di thread terpisah agar Flask tidak terblokir
    thread = Thread(target=pyrogram_login_thread, args=(api_id, api_hash,), daemon=True)
    thread.start()
    
    # Beri sedikit waktu agar thread sempat set status PROMPT_USER_INPUT
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
        # VALIDASI Sederhana: Memastikan string Pyrogram valid
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


# --- FUNGSI UTAMA RUNTIME (Tidak Berubah) ---

def run_flask(db_client, initial_token):
    STATE["db"] = db_client
    STATE["tunnel_token"] = initial_token

    # Atur level log tepat sebelum server dimulai
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    thread = Thread(target=lambda: app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False), daemon=True)
    thread.start()

    public_url = None
    if STATE.get("tunnel_token"):
        try:
            ngrok.set_auth_token(STATE["tunnel_token"])
            public_url = ngrok.connect(PORT).public_url
            STATE["tunnel_url"] = public_url
        except Exception as e:
            # Jika ngrok gagal start, jangan crash
            print(f"⚠️ Peringatan: Gagal menjalankan tunnel ngrok dengan token: {e}")

    return public_url