import os
from flask import Flask, render_template, request, send_file
from util import format_size, get_disk_usage, _is_within_root, list_dir

app = Flask(__name__)

def create_app(ROOT_PATH):
    @app.route("/")
    def index():
        req_path = request.args.get("path", ROOT_PATH)
        abs_path = os.path.abspath(req_path) if os.path.exists(req_path) else ROOT_PATH
        colab_total, colab_used, colab_percent = get_disk_usage(ROOT_PATH)
        files = list_dir(abs_path, ROOT_PATH)
        return render_template("main.html", path=abs_path, files=files,
                               colab_total=colab_total, colab_used=colab_used, colab_percent=colab_percent)
    return app