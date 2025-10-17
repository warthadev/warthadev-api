# ... (impor lainnya)
from flask import Flask, jsonify, request, render_template, redirect, url_for # render_template ditambahkan
import os.path as os_path # Impor os.path untuk digunakan di template
# ...

# ... (Fungsi format_size, get_dir_size, get_disk_usage, list_dir tetap sama) ...

# --- HAPUS FUNGSI generate_html_template_simple ---
# Fungsi ini tidak diperlukan lagi karena templating akan dilakukan oleh Jinja2

# ...

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates"))
# ^^^ PENTING: Menentukan lokasi folder templates relative ke flask.py

# ... (rute lainnya)

@app.route("/")
def index():
    path = request.args.get('path', ROOT_PATH)
    path = os.path.abspath(path)

    if not path.startswith(ROOT_PATH) or not os.path.exists(path): path = ROOT_PATH
    if path == DRIVE_MOUNT_PATH and os.path.exists(os.path.join(path, "MyDrive")): path = os.path.join(path, "MyDrive")

    all_files = list_dir(path)
    # parent_path tidak lagi perlu dilewatkan karena tombol kembali menggunakan JS history.back()

    colab_total, colab_used, _, colab_percent = get_disk_usage(ROOT_PATH)
    drive_total, drive_used, _, drive_percent = get_disk_usage(DRIVE_MOUNT_PATH) if os.path.exists(DRIVE_MOUNT_PATH) else (0, 0, 0, 0)

    # Menggunakan render_template dan mengirim semua data yang diperlukan
    return render_template(
        "index.html",
        path=path,
        files=all_files,
        # Data Disk
        colab_total=colab_total,
        colab_used=colab_used,
        colab_percent=colab_percent,
        drive_total=drive_total,
        drive_used=drive_used,
        drive_percent=drive_percent,
        # Fungsi yang dapat diakses di template
        format_size=format_size,
        # Konstanta untuk keperluan template (seperti home path)
        root_path=ROOT_PATH,
        drive_mount_path=DRIVE_MOUNT_PATH,
        os_path=os_path # Digunakan untuk os_path.exists/join di template
    )

# ... (lanjutkan dengan rute set_tunnel, status, dan fungsi run_flask)
