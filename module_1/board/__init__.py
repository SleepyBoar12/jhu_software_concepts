from flask import Flask
"""
Starting this program creates the web application with Flask
"""

def create_app():
    app = Flask(__name__)

    from board.pages import bp
    app.register_blueprint(bp)

    return app
