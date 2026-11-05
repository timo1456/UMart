import os
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "store.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def init_db():
    with app.app_context():
        db.create_all()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password or not role:
            flash("Please complete all fields.", "error")
        elif len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
        elif password != confirm_password:
            flash("The passwords do not match.", "error")
        else:
            user = User(
                username=username,
                email=email,
                role=role,
                password_hash=generate_password_hash(password),
            )
            try:
                db.session.add(user)
                db.session.commit()
                session.clear()
                session["user_id"] = user.id
                session["username"] = user.username
                session["role"]= user.role
                flash("Your UMart account has been created.", "success")
                return redirect(url_for("dashboard"))
            except IntegrityError:
                db.session.rollback()
                flash("That username or email is already registered.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            or_(User.email == identity, User.username == identity, User.role == identity)
        ).first()

        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid username/email or password.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    if "user" not in session:
        return redirect("/login")

    if session["role"] == "buyer":
        return render_template(
            "buyer-dashboard.html",
            user=session["user"]
        )
    
    if session["role"] == "seller":
            return render_template(
                "seller-dashboard.html",
                user=session["user"]
            )
    

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
