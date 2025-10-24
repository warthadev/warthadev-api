#!/usr/bin/env python3
# app.py - Inti aplikasi Flask dan Eksekusi
import os, sys, logging, importlib.util, time
from flask import Flask
from werkzeug.serving import run_simple
# Import modul lokal yang baru
import utils, tunnel, views

# --- KONFIGURASI (Akan di-overwrite oleh bootloader Colab) ---
ROOT_PATH = "/content" 
PORT = 8000
# Variabel yang disuntikkan oleh bootloader, perlu dipertahankan di sini
DECRYPTION_SUCCESS = False 

logging.getLogger("werkzeug").setLevel(logging.ERROR)

try:
    # BASE_DIR menunjuk ke /tmp/warthadev-api
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

TEMPLATE_FOLDER = os.path.join(BASE_DIR, "html")
STATIC_FOLDER_ROOT = BASE_DIR
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)


# --- FLASK APP INITIALIZATION ---
app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")
app.jinja_env.globals.update(format_size=utils.format_size, os_path=os.path)

# Suntikkan ROOT_PATH dan DECRYPTION_SUCCESS ke modul views (opsional tapi disarankan)
views.ROOT_PATH = ROOT_PATH
views.DECRYPTION_SUCCESS = DECRYPTION_SUCCESS
views.TEMPLATE_FOLDER = TEMPLATE_FOLDER
views.app = app # Beri views akses ke instance app

# Mendaftarkan rute dari views.py
app.add_url_rule('/', view_func=views.index, methods=['GET'])
app.add_url_rule('/file', view_func=views.open_file, methods=['GET'])

# --- TUNNEL EXECUTION ---
def run_flask_and_tunnel():
    """Menggunakan fungsi dari modul tunnel yang baru."""
    # Pastikan variabel di modul tunnel sudah benar
    tunnel.PORT = PORT
    tunnel.app = app
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
