#!/usr/bin/env python3
# app.py - Inti aplikasi Flask dan Eksekusi (Struktur Impor Final yang Stabil)
import os, sys, logging, time
from flask import Flask
from werkzeug.serving import run_simple

# --- KONFIGURASI (Akan di-overwrite oleh bootloader Colab) ---
ROOT_PATH = "/content" 
PORT = 8000
DECRYPTION_SUCCESS = False 

# Variabel Global untuk modul (akan diisi di setup_app)
global utils, tunnel, views, app

logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)


def setup_app():
    """
    Fungsi ini menangani semua impor modul lokal, inisialisasi Flask,
    dan penyuntikan variabel untuk menghindari konflik urutan impor (ModuleNotFoundError).
    """
    global utils, tunnel, views, app
    
    # --- 1. IMPORT MODUL LOKAL ---
    # Impor modul lokal dilakukan di sini agar prosesnya terisolasi dan tertangkap.
    try:
        import utils
        import tunnel
        import views
    except ImportError as e:
        print(f"FATAL ERROR: Gagal mengimpor modul lokal. Pastikan /python/ ada di sys.path. Error: {e}")
        # Jika impor gagal, program harus dihentikan
        raise RuntimeError(f"Gagal memuat modul Flask: {e}") from e

    # --- 2. FLASK APP INITIALIZATION ---
    app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")
    
    # Suntikkan fungsi utility ke Jinja Environment
    app.jinja_env.globals.update(format_size=utils.format_size, os_path=os.path)

    # --- 3. PENYUNTIKAN VARIABEL GLOBAL KE VIEWS DAN TUNNEL ---
    # Menyuntikkan variabel yang dibutuhkan oleh fungsi-fungsi di modul
    
    # Views membutuhkan konfigurasi path dan instance app
    views.ROOT_PATH = ROOT_PATH
    views.DECRYPTION_SUCCESS = DECRYPTION_SUCCESS
    views.TEMPLATE_FOLDER = TEMPLATE_FOLDER
    views.app = app # SUNTIKKAN INSTANCE APP UTAMA KE MODUL VIEWS

    # Tunnel membutuhkan port dan instance app
    tunnel.PORT = PORT
    tunnel.app = app # SUNTIKKAN INSTANCE APP UTAMA KE MODUL TUNNEL
    
    # --- 4. PENDAFTARAN RUTE ---
    # Rute didaftarkan menggunakan app.add_url_rule (views.py TIDAK boleh punya @app.route)
    app.add_url_rule('/', view_func=views.index, methods=['GET'])
    app.add_url_rule('/file', view_func=views.open_file, methods=['GET'])

    print("✅ Aplikasi Flask berhasil diinisialisasi dan modul disuntikkan.")
    
    # Return instance app yang sudah siap
    return app


# --- TUNNEL EXECUTION ---
def run_flask_and_tunnel():
    """Menggunakan fungsi dari modul tunnel yang baru."""
    # Dipanggil setelah setup_app()
    if 'tunnel' not in globals():
        raise RuntimeError("Modul tunnel belum diimpor. Jalankan setup_app() dulu.")
    
    tunnel.run_flask_and_tunnel()


# --- MAIN ---
if __name__=="__main__":
    print(f"Starting app.py -> ROOT_PATH={ROOT_PATH} PORT={PORT}")
    os.makedirs(ROOT_PATH,exist_ok=True)
    try:
        # Jalankan setup
        app = setup_app()
        # Jalankan server
        run_flask_and_tunnel()
        
        print("Menjaga program tetap hidup (Ctrl+C untuk keluar)...")
        while True:
            time.sleep(1)
            
    except RuntimeError as e:
        print(f"❌ Gagal menjalankan aplikasi: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Terminated."); sys.exit(0)
