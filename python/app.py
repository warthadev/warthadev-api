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
        sys.exit(1)

    # --- 2. INISIALISASI FLASK ---
    app = Flask(__name__, 
                static_folder=STATIC_FOLDER_ROOT, # Static dari root (untuk assets)
                template_folder=TEMPLATE_FOLDER) # Template dari folder 'html'

    # --- 3. SUNTIKKAN VARIABEL GLOBAL ---
    # Variabel utama
    views.ROOT_PATH = ROOT_PATH
    views.DECRYPTION_SUCCESS = DECRYPTION_SUCCESS
    views.TEMPLATE_FOLDER = TEMPLATE_FOLDER
    
    # Instance Flask
    views.app = app # SUNTIKKAN INSTANCE APP UTAMA KE MODUL VIEWS

    # Tunnel membutuhkan port dan instance app
    tunnel.PORT = PORT
    tunnel.app = app # SUNTIKKAN INSTANCE APP UTAMA KE MODUL TUNNEL
    
    # --- 4. PENDAFTARAN RUTE ---
    # Rute didaftarkan menggunakan app.add_url_rule (views.py TIDAK boleh punya @app.route)
    app.add_url_rule('/', view_func=views.index, methods=['GET'])
    app.add_url_rule('/file', view_func=views.open_file, methods=['GET'])
    # BARIS BARU: Route untuk melayani thumbnail
    app.add_url_rule('/thumb', view_func=views.serve_thumbnail, methods=['GET'])

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
            
    except Exception as e:
        print(f"ERROR Fatal di main loop: {e}")
