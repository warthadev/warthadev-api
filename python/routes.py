from flask import Flask, request, render_template, send_file
from .utils import get_disk_usage, list_dir
import os

def register_routes(app, root_path):
    @app.route("/")
    def index():
        req_path = request.args.get("path", root_path)
        try: abs_path=os.path.abspath(req_path)
        except: abs_path=root_path
        if not os.path.exists(abs_path): abs_path=root_path

        colab_total, colab_used, colab_percent = get_disk_usage(root_path)
        files = list_dir(abs_path, root_path)
        tpl = "main.html"
        if not os.path.exists(os.path.join("html", tpl)):
            items_html = "".join(f"<div>{'DIR' if f['is_dir'] else 'FILE'} - <a href='/?path={f['full_path']}'>{f['name']}</a> - {f['size']}</div>" for f in files)
            return f"<html><body><h3>{abs_path}</h3>{items_html}</body></html>"
        return render_template(tpl, path=abs_path, root_path=root_path, files=files,
                               colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent)

    @app.route("/file")
    def open_file():
        p = request.args.get("path","")
        if not p: return "Path missing",400
        try: abs_path=os.path.abspath(p)
        except: return "Invalid path",400
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path): return "File cannot be opened.",404
        text_exts={'.txt','.py','.csv','.md','.log','.json','.yml','.yaml','.html','.css','.js'}
        ext=os.path.splitext(abs_path)[1].lower()
        if ext in text_exts:
            try:
                with open(abs_path,"r",encoding="utf-8",errors="ignore") as fh: content=fh.read()
                return f"<pre>{content.replace('</','&lt;/')}</pre>"
            except Exception as e: return f"Failed to read file: {e}",500
        try: return send_file(abs_path, as_attachment=True)
        except Exception as e: return f"Failed to send file: {e}",500