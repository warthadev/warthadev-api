#!/usr/bin/env python3
# app.py - Inti aplikasi Flask dan Eksekusi (Struktur Impor yang Lebih Stabil)
import os, sys, logging, time
from flask import Flask
from werkzeug.serving import run_simple

# Hapus Impor Modul Lokal di sini (Akan dilakukan di bawah)

# --- KONFIGURASI (Akan di-overwrite oleh bootloader Colab) ---
ROOT_PATH = "/content" 
PORT = 8000
DECRYPTION_SUCCESS = False 

logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)


# --- FLASK APP INITIALIZATION ---
# Buat instance app dulu sebelum mengimpor views/tunnel
app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")


# --- IMPORT MODUL LOKAL & PENYUNTIKAN VARIABEL ---
# Impor modul lokal sekarang (sys.path sudah diatur di Colab bootloader)
try:
    import utils
    import tunnel
    import views
except ImportError as e:
    # Jika masih gagal, Colab bootloader GAGAL menambahkan PYTHON_DIR ke sys.path.
    print(f"FATAL ERROR: Gagal mengimpor modul lokal. Pastikan /python/ ada di sys.path. Error: {e}")
    sys.exit(1)


# Suntikkan fungsi utility ke Jinja Environment
app.jinja_env.globals.update(format_size=utils.format_size, os_path=os.path)

# Suntikkan variabel ke modul views
views.ROOT_PATH = ROOT_PATH
views.DECRYPTION_SUCCESS = DECRYPTION_SUCCESS
views.TEMPLATE_FOLDER = TEMPLATE_FOLDER
views.app = app # SUNTIKKAN INSTANCE APP UTAMA KE MODUL VIEWS

# Suntikkan variabel ke modul tunnel
tunnel.PORT = PORT
tunnel.app = app # SUNTIKKAN INSTANCE APP UTAMA KE MODUL TUNNEL


# Mendaftarkan rute dari views.py (Menggunakan app.add_url_rule adalah cara terbaik)
app.add_url_rule('/', view_func=views.index, methods=['GET'])
app.add_url_rule('/file', view_func=views.open_file, methods=['GET'])


# --- TUNNEL EXECUTION ---
def run_flask_and_tunnel():
    """Menggunakan fungsi dari modul tunnel yang baru."""
    # Semua variabel sudah disuntikkan ke modul tunnel di atas
    tunnel.run_flask_and_tunnel()


# --- MAIN ---
if __name__=="__main__":
    print(f"Starting app.py -> ROOT_PATH={ROOT_PATH} PORT={PORT}")
    os.makedirs(ROOT_PATH,exist_ok=True)
    try:
        run_flask_and_tunnel()
        print("Menjaga program tetap hidup (Ctrl+C untuk keluar)...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminated."); sys.exit(0)
