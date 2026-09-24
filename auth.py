from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import create_user, get_user_by_email

auth_bp = Blueprint("auth", __name__)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped

@auth_bp.get("/login")
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html")

@auth_bp.post("/login")
def login_submit():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email.endswith("@gmail.com"):
        flash("Please use a Gmail address.", "error")
        return redirect(url_for("auth.login"))
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid Gmail address or password.", "error")
        return redirect(url_for("auth.login"))
    session.clear()
    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    return redirect(url_for("dashboard.dashboard"))

@auth_bp.get("/register")
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("register.html")

@auth_bp.post("/register")
def register_submit():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    if not email.endswith("@gmail.com"):
        flash("Registration requires a Gmail address.", "error")
        return redirect(url_for("auth.register"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("auth.register"))
    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.register"))
    if get_user_by_email(email):
        flash("An account with this Gmail address already exists.", "error")
        return redirect(url_for("auth.login"))
    user_id = create_user(email, generate_password_hash(password))
    session.clear()
    session["user_id"] = user_id
    session["user_email"] = email
    return redirect(url_for("dashboard.dashboard"))

@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
