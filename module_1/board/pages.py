from flask import Blueprint, render_template
"""
These are the blueprints to link render and link different templates by extending the base
"""

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    return render_template("home.html")

@bp.route("/about")
def about():
    return render_template("about.html")

@bp.route("/projects")
def projects():
    return render_template("projects.html")

@bp.route("/contact")
def contact():
    return render_template("contacts.html")
