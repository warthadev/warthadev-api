import os
from flask import Flask, render_template, send_file, request
from utils import format_size, get_disk_usage, list_dir, _is_within_root

def create_app(root_path, template_path="/tmp/warthadev-api/html"):
    app = Flask(
        __name__, 
        template_folder=template_path,  # pakai template di path lo
        static_folder=root_path,
        static_url_path="/static"
    )
    app.jinja_env.globals.update(format_size=format_size, os_path=os.path)

    @app.route("/")
    def index():
        req_path = request.args.get("path", root_path)
        try: abs_path=os.path.abspath(req_path)
        except: abs_path=root_path
        if not _is_within_root(abs_path, root_path) or not os.path.exists(abs_path):
            abs_path = root_path

        colab_total, colab_used, colab_percent = get_disk_usage(root_path)
        drive_mount_path = "/content/drive"
        drive_total, drive_used, drive_percent = get_disk_usage(drive_mount_path)
        files = list_dir(abs_path, root_path)

        # langsung render template, tanpa HTML fallback
        return render_template(
            "main.html",
            path=abs_path,
            root_path=root_path,
            files=files,
            colab_total=colab_total,
            colab_used=colab_used,
            colab_percent=colab_percent,
            drive_total=drive_total,
            drive_used=drive_used,
            drive_percent=drive_percent,
            drive_mount_path=drive_mount_path
        )

    @app.route("/file")
    def open_file():
        p = request.args.get("path","")
        if not p: return "Path missing",400
        try: abs_path=os.path.abspath(p)
        except: return "Invalid path",400
        if not _is_within_root(abs_path, root_path) or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            return "File cannot be opened.",404
        text_exts={'.txt','.py','.csv','.md','.log','.json','.yml','.yaml','.html','.css','.js'}
        ext=os.path.splitext(abs_path)[1].lower()
        if ext in text_exts:
            try:
                with open(abs_path,"r",encoding="utf-8",errors="ignore") as fh:
                    content=fh.read()
                return f"<pre>{content.replace('</','&lt;/')}</pre>"
            except Exception as e:
                return f"Failed to read file: {e}",500
        try: return send_file(abs_path, as_attachment=True)
        except Exception as e: return f"Failed to send file: {e}",500

    return app