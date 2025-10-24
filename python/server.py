from flask import Flask, render_template, send_file, request
import os
from utils import format_size, get_disk_usage, get_directory_size, get_file_icon_class
from config import ROOT_PATH, TEMPLATE_FOLDER, STATIC_FOLDER_ROOT

app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER_ROOT, static_url_path="/static")

def _is_within_root(path):
    try:
        return os.path.commonpath([os.path.realpath(ROOT_PATH), os.path.realpath(path)]) == os.path.realpath(ROOT_PATH)
    except: return False

def list_dir(path):
    files = []
    if not os.path.exists(path): return files
    for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower())):
        full_path = os.path.join(path, name)
        if os.path.islink(full_path) and not _is_within_root(full_path): continue
        is_dir = os.path.isdir(full_path)
        try:
            size_bytes = get_directory_size(full_path) if is_dir else os.path.getsize(full_path)
            size_formatted = format_size(size_bytes)
            icon_class = "fa-folder" if is_dir else get_file_icon_class(name)
        except: size_formatted, icon_class = "Error", "fa-exclamation"
        files.append({"name":name, "is_dir":is_dir, "full_path":full_path, "size":size_formatted, "icon_class":icon_class})
    return files

@app.route("/")
def index():
    req_path = request.args.get("path", ROOT_PATH)
    abs_path = os.path.abspath(req_path)
    if not _is_within_root(abs_path) or not os.path.exists(abs_path): abs_path = ROOT_PATH

    colab_total, colab_used, colab_percent = get_disk_usage(ROOT_PATH)
    drive_total, drive_used, drive_percent = get_disk_usage("/content/drive")

    files = list_dir(abs_path)
    tpl = "main.html"
    if not os.path.exists(os.path.join(TEMPLATE_FOLDER, tpl)):
        return f"<html><body><h3>{abs_path}</h3>" + "".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - {f['name']}</div>" for f in files) + "</body></html>"

    return render_template(tpl, path=abs_path, root_path=ROOT_PATH, files=files,
        colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent,
        drive_total=drive_total, drive_used=drive_used, drive_percent=drive_percent,
        drive_mount_path="/content/drive")

@app.route("/file")
def open_file():
    p = request.args.get("path","")
    if not p: return "Path missing",400
    abs_path = os.path.abspath(p)
    if not _is_within_root(abs_path) or not os.path.isfile(abs_path): return "File cannot be opened.",404
    text_exts = {'.txt','.py','.csv','.md','.log','.json','.yml','.yaml','.html','.css','.js'}
    ext = os.path.splitext(abs_path)[1].lower()
    if ext in text_exts:
        try:
            with open(abs_path,"r",encoding="utf-8",errors="ignore") as fh: content=fh.read()
            return f"<pre>{content.replace('</','&lt;/')}</pre>"
        except Exception as e: return f"Failed to read file: {e}",500
    try: return send_file(abs_path, as_attachment=True)
    except Exception as e: return f"Failed to send file: {e}",500