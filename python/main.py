from tunnel import run_flask_and_tunnel
from config import ROOT_PATH
import os, sys, time, traceback

def main():
    print(f"🚀 Starting Flask + Tunnel | ROOT_PATH={ROOT_PATH}")
    os.makedirs(ROOT_PATH, exist_ok=True)
    try:
        run_flask_and_tunnel()
        print("💤 Menjaga server tetap hidup...")
        while True:
            time.sleep(1)
    except Exception as e:
        print("❌ Terjadi error saat menjalankan Flask + Tunnel:")
        print("=" * 60)
        print(traceback.format_exc())
        print("=" * 60)
        print("💡 Cek apakah template folder sudah benar (misal: /tmp/warthadev-api/html)")
        sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Dihentikan.")
        sys.exit(0)

if __name__ == "__main__":
    main()