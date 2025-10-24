from tunnel import run_flask_and_tunnel
from config import ROOT_PATH
import os, sys, time, traceback, subprocess

PORT = 8000  # port default

def kill_port(port):
    try:
        result = subprocess.run(f"lsof -ti:{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().splitlines()
            print(f"⚠️ Port {port} dipake PID: {', '.join(pids)} — kill dulu...")
            subprocess.run(f"kill -9 {' '.join(pids)}", shell=True)
            print(f"✅ Port {port} udah bebas.")
        else:
            print(f"Port {port} kosong, lanjut...")
    except Exception as e:
        print(f"❌ Gagal cek/kill port {port}: {e}")

def main():
    print(f"🚀 Starting Flask + Tunnel | ROOT_PATH={ROOT_PATH} | PORT={PORT}")
    os.makedirs(ROOT_PATH, exist_ok=True)
    kill_port(PORT)
    try:
        run_flask_and_tunnel()
        print("💤 Menjaga server tetap hidup...")
        while True:
            time.sleep(1)
    except Exception:
        print("❌ Terjadi error saat menjalankan Flask + Tunnel:")
        print("=" * 60)
        print(traceback.format_exc())
        print("=" * 60)
        sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Dihentikan.")
        sys.exit(0)

if __name__ == "__main__":
    main()