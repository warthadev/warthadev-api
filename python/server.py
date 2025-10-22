# server.py
import os, threading, time, json
from flask import Flask, render_template, request, send_file, jsonify
from .utils import list_dir, format_size
from .tunnel import TunnelManager

app = Flask(__name__, template_folder=None)  # we will render simple HTML or static if provided

# Attach manager externally (set by main)
tunnel_manager = None
ROOT_PATH = os.environ.get("NEWFLASK_ROOT", "/content")

@app.route("/")
def index():
    path = request.args.get("path", ROOT_PATH)
    try:
        files = list_dir(path)
    except Exception as e:
        files = [{"name": f"ERROR: {e}", "is_dir": False, "full_path": "", "size": "", "size_bytes":0, "icon":"fa-exclamation-triangle"}]
    # Very simple listing (user can replace with template in folder)
    items = []
    for f in files:
        if f["is_dir"]:
            items.append(f"[DIR] <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}")
        else:
            items.append(f"[FILE] <a href='/file?path={f['full_path']}'>{f['name']}</a> - {f['size']}")
    body = "<br/>".join(items)
    return f"<h3>Root: {ROOT_PATH}</h3><div>{body}</div><hr/><div>Toggle tunnel: <a href='/tunnel/status'>status</a> | <a href='/tunnel/start'>start</a> | <a href='/tunnel/stop'>stop</a></div>"

@app.route("/file")
def open_file():
    p = request.args.get("path","")
    if not p:
        return "Path missing",400
    if not os.path.exists(p):
        return "Not found",404
    if os.path.isdir(p):
        return "Is a directory",400
    # for text files, show inline
    text_exts = {'.txt','.py','.md','.log','.json','.csv','.html','.css','.js'}
    ext = os.path.splitext(p)[1].lower()
    if ext in text_exts:
        try:
            with open(p,'r',encoding='utf-8',errors='ignore') as fh:
                return "<pre>"+fh.read().replace("</","&lt;/")+"</pre>"
        except Exception as e:
            return f"Failed to read: {e}",500
    try:
        return send_file(p, as_attachment=True)
    except Exception as e:
        return f"Failed to send: {e}",500

# --- Tunnel control endpoints ---
@app.route("/tunnel/start", methods=["GET","POST"])
def tunnel_start():
    global tunnel_manager
    if tunnel_manager is None:
        return jsonify({"ok":False,"msg":"tunnel manager not available"}),500
    port = request.args.get("port")
    if port:
        try:
            port = int(port)
        except:
            return jsonify({"ok":False,"msg":"invalid port"}),400
    else:
        port = int(os.environ.get("NEWFLASK_PORT","8000"))
    res = tunnel_manager.start(port)
    return jsonify(res)

@app.route("/tunnel/stop", methods=["POST","GET"])
def tunnel_stop():
    global tunnel_manager
    if tunnel_manager is None:
        return jsonify({"ok":False,"msg":"tunnel manager not available"}),500
    res = tunnel_manager.stop()
    return jsonify(res)

@app.route("/tunnel/status")
def tunnel_status():
    global tunnel_manager
    if tunnel_manager is None:
        return jsonify({"ok":False,"msg":"tunnel manager not available"}),500
    return jsonify(tunnel_manager.status())