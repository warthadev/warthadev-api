# newflask.py

import os, subprocess, re, time
from flask import Flask, render_template_string, send_file, request
from threading import Thread

# Config
ROOT_PATH = "/content"
PORT = 8000
# Variabel ini akan diupdate dari script utama sebelum exec_module
DECRYPTION_SUCCESS = False

def list_dir(path):
    files = []
    try:
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            files.append({
                "name": f,
                "is_dir": os.path.isdir(full_path),
                "full_path": full_path
            })
    except Exception as e:
        print(f"list_dir error: {e}")
    return sorted(files, key=lambda x: (not x['is_dir'], x['name'].lower()))

def generate_html(path, files, parent_path):
    file_html = ""
    for f in files:
        link = f'/?path={f["full_path"]}' if f['is_dir'] else f'/file?path={f["full_path"]}'
        icon = "📁" if f['is_dir'] else "📄"
        file_html += f"<li>{icon} <a href='{link}'>{f['name']}</a></li>"

    config_status = "✅ Config Didekripsi" if DECRYPTION_SUCCESS else "❌ GAGAL Dekripsi. Cek error di output Colab."

    return f'''
    <html>
    <head><meta charset="UTF-8"><title>File Manager</title></head>
    <body>
        <h1>Colab File Manager</h1>
        <p>Status Konfigurasi: <b>{config_status}</b></p>
        <hr>
        <p>Path Saat Ini: <b>{path}</b></p>
        {f'<p><a href="/?path={parent_path}">⬆️ Kembali ke {os.path.basename(parent_path) or "ROOT"}</a></p>' if parent_path else ''}
        <ul>{file_html}</ul>
    </body>
    </html>
    '''

app = Flask(__name__)

@app.route('/')
def index():
    path = request.args.get('path', ROOT_PATH)
    path = os.path.abspath(path)
    if not path.startswith(ROOT_PATH) or not os.path.exists(path):
        path = ROOT_PATH
    all_files = list_dir(path)
    parent_path = os.path.dirname(path) if path != ROOT_PATH else None
    return render_template_string(generate_html(path, all_files, parent_path))

@app.route('/file')
def open_file():
    path = request.args.get('path')
    path = os.path.abspath(path)
    if not path.startswith(ROOT_PATH) or not os.path.isfile(path):
        return "File tidak bisa dibuka.", 404
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.txt','.py','.csv','.md','.log','.json','.yml']:
        try:
            with open(path,"r",encoding="utf-8",errors='ignore') as f:
                return f"<pre>{f.read()}</pre>"
        except Exception as e:
            return f"Gagal membaca file. ({e})", 500
    else:
        return send_file(path, as_attachment=True)

def run_flask_and_tunnel():
    
    def run_flask():
        app.run(host="0.0.0.0", port=PORT, threaded=True)
    Thread(target=run_flask, daemon=True).start()

    print("🔽 Mengunduh cloudflared...")
    os.system('wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared-linux-amd64')
    os.system('chmod +x cloudflared-linux-amd64')
    print("🔧 cloudflared siap.")

    print("🚀 Menjalankan Cloudflare Quick Tunnel...")
    proc = subprocess.Popen(
        ["./cloudflared-linux-amd64", "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    public_url = None
    for _ in range(30):
        line = proc.stdout.readline()
        if line:
            print(line.strip())
            m = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
            if m:
                public_url = m.group(1)
                break
        time.sleep(1)
        
    print("\n" + "="*50)
    if public_url:
        print("             ✅ SETUP SELESAI ✅")
        print(f"🔗 LINK PUBLIC FILE MANAGER: **{public_url}**")
    else:
        print("             ❌ GAGAL TUNNEL ❌")
        print("Cek log Cloudflared di atas untuk detail error.")
    print("==================================================")
