from flask import Blueprint, render_template, session
from routes.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.get("/")
def home():
    if "user_id" in session:
        return render_template("dashboard.html")
    return render_template("index.html")

@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@dashboard_bp.get("/map")
@login_required
def map_page():
    return render_template("map.html")
