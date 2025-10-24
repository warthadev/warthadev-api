from tunnel import run_flask_and_tunnel
from config import ROOT_PATH
import os, sys, time

def main():
    print(f"🚀 Starting Flask + Tunnel | ROOT_PATH={ROOT_PATH}")
    os.makedirs(ROOT_PATH, exist_ok=True)
    try:
        run_flask_and_tunnel()
        print("💤 Menjaga server tetap hidup...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Dihentikan.")
        sys.exit(0)

if __name__ == "__main__":
    main()