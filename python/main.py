#!/usr/bin/env python3
# main.py - versi diperkuat modular: DNS-check + auto-retry untuk trycloudflare
import os, sys, time, re
from threading import Thread

# Import modul-modul yang sudah dibuat
from . import config
from . import utils
from . import server

def run_flask_and_tunnel():
    # 1. Start Flask server di thread terpisah
    t = Thread(target=server.start_flask_server)
    t.start()

    # 2. Pastikan cloudflared ada
    if not utils.ensure_cloudflared():
        print("cloudflared tidak tersedia. Tidak bisa membuat terowongan."); return

    proc = None
    restarts = 0
    public_url = None

    # 3. Looping untuk Cloudflared dengan retry
    while restarts < config.CLOUDFLARED_RESTARTS:
        restarts += 1
        print(f"[TUNNEL] Mencoba membuat terowongan (attempt {restarts}/{config.CLOUDFLARED_RESTARTS})...")
        
        # Argumen cloudflared
        args = [config.CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{config.PORT}", 
                "--no-autoupdate", "--loglevel", "info", "--edge-ip-version", "auto"]
        
        proc = utils.start_cloudflared(args)
        if not proc:
            print("[TUNNEL] Gagal start cloudflared, retrying...")
            time.sleep(2)
            continue

        start = time.time()
        public_url = None
        
        # 4. Parsing stdout untuk mendapatkan URL
        while time.time() - start < config.CLOUDFLARE_TIMEOUT:
            try: line = proc.stdout.readline()
            except Exception: line = ""
            if not line:
                time.sleep(config.RETRY_DELAY)
                if proc.poll() is not None:
                     print("[TUNNEL] Proses cloudflared mati tak terduga.")
                     break
                continue
            line_str = line.strip()
            print(line_str)
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line_str)
            if m:
                public_url = m.group(1)
                print(f"[TUNNEL] URL ditemukan di stdout: {public_url}")
                break

        if not public_url or proc.poll() is not None:
            print("[TUNNEL] Tidak dapat menemukan URL atau proses mati. Akan restart cloudflared dan coba lagi.")
            utils.stop_proc(proc)
            time.sleep(2)
            continue
        
        # 5. DNS Propagation Check
        hostname = re.sub(r'^https?://', '', public_url).split('/')[0]
        print(f"[DNS] Menunggu hostname {hostname} ter-resolve (timeout {config.DNS_CHECK_TIMEOUT}s)...")
        dns_start = time.time()
        resolved = False
        while time.time() - dns_start < config.DNS_CHECK_TIMEOUT:
            if utils.doh_resolves(hostname, timeout=3):
                resolved = True
                break
            if proc.poll() is not None:
                print("[DNS] Cloudflared mati saat menunggu DNS. Membatalkan DNS check.")
                break
            print("[DNS] Belum ter-resolve, menunggu 1s lalu retry...")
            time.sleep(1)

        if resolved:
            print("\n" + "="*50)
            print("URL PUBLIK ANDA (dan sudah resolved):")
            print(f"  {public_url}")
            print("="*50 + "\n")
            return
        else:
            print("[DNS] Hostname masih belum ter-resolve setelah timeout atau proses mati. Akan restart cloudflared dan coba lagi.")
            utils.stop_proc(proc)
            time.sleep(2)
            continue
            
    # 6. Final status
    if proc and proc.poll() is None:
        print("[TUNNEL] Semua percobaan restart habis, tapi proses cloudflared masih berjalan — periksa log di atas.")
    else:
        print("[TUNNEL] Semua percobaan gagal. Tidak ada tunnel aktif.")

# --- MAIN EXECUTION ---
if __name__=="__main__":
    print(f"Starting newflask.py -> ROOT_PATH={config.ROOT_PATH} PORT={config.PORT}")
    os.makedirs(config.ROOT_PATH,exist_ok=True)
    try:
        run_flask_and_tunnel()
        print("Menjaga program tetap hidup (Ctrl+C untuk keluar)...")
        # Loop utama agar program tidak keluar
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminated."); sys.exit(0)
