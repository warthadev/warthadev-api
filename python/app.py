from flask import Flask
from .routes import register_routes

def create_app(root_path="/content"):
    app = Flask(__name__, template_folder="html", static_folder=".", static_url_path="/static")
    register_routes(app, root_path)
    return app