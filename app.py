import os
from functools import wraps
from pathlib import Path

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, or_, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, Stock, db

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "store.db"
ALLOWED_ROLES = {"buyer", "seller"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_SIZE + 1024 * 1024

db.init_app(app)


def init_db():
    with app.app_context():
        db.create_all()
        columns = {column["name"] for column in inspect(db.engine).get_columns("stock")}
        with db.engine.begin() as connection:
            if "seller_id" not in columns:
                connection.execute(text("ALTER TABLE stock ADD COLUMN seller_id INTEGER REFERENCES user(id)"))
            if "pr_img_mimetype" not in columns:
                connection.execute(text("ALTER TABLE stock ADD COLUMN pr_img_mimetype VARCHAR(50)"))


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id is not None else None


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if current_user() is None:
            session.clear()
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def seller_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(**kwargs):
        if current_user().role != "seller":
            flash("Only seller accounts can add products.", "error")
            return redirect(url_for("dashboard"))
        return view(**kwargs)
    return wrapped_view


@app.errorhandler(413)
def file_too_large(_error):
    flash("The image is too large. Maximum image size is 5 MB.", "error")
    return redirect(url_for("add_products_page"))


@app.route("/")
def home():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password or not role:
            flash("Please complete all fields.", "error")
        elif len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
        elif role not in ALLOWED_ROLES:
            flash("Please select a valid account role.", "error")
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
                flash("Your UMart account has been created.", "success")
                return redirect(url_for("dashboard"))
            except SQLAlchemyError:
                db.session.rollback()
                flash("That username or email may already be registered.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            or_(User.email == identity, User.username == identity)
        ).first()

        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid username/email or password.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()

    if user.role == "buyer":
        search = request.args.get("search", "").strip()
        products_query = Stock.query
        if search:
            term = f"%{search}%"
            products_query = products_query.filter(
                or_(Stock.pr_name.ilike(term), Stock.pr_category.ilike(term))
            )
        products = products_query.order_by(Stock.id.desc()).all()
        return render_template(
            "buyer-dashboard.html",
            username=user.username,
            search=search,
            products=products,
        )

    if user.role == "seller":
        return render_template("seller-dashboard.html", username=user.username)

    session.clear()
    flash("Your account has an invalid role. Please contact support.", "error")
    return redirect(url_for("login"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/add_products_page")
@seller_required
def add_products_page():
    return render_template("add-products.html")


@app.route("/add-products", methods=["GET", "POST"])
@seller_required
def add_products():
    if request.method == "GET":
        return redirect(url_for("add_products_page"))

    name = request.form.get("pr-name", "").strip()
    price_text = request.form.get("pr-price", "").strip()
    category = request.form.get("pr-category", "").strip()
    image = request.files.get("pr-img")

    if not name or not category or not price_text:
        flash("Product name, price and category are required.", "error")
        return redirect(url_for("add_products_page"))

    try:
        price = int(price_text)
        if price <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid price greater than zero.", "error")
        return redirect(url_for("add_products_page"))

    image_data = None
    image_mimetype = None
    if image and image.filename:
        if image.mimetype not in ALLOWED_IMAGE_TYPES:
            flash("Upload a JPG, PNG, WEBP or GIF image.", "error")
            return redirect(url_for("add_products_page"))
        image_data = image.read(MAX_IMAGE_SIZE + 1)
        if not image_data or len(image_data) > MAX_IMAGE_SIZE:
            flash("The image is empty or exceeds the 5 MB limit.", "error")
            return redirect(url_for("add_products_page"))
        image_mimetype = image.mimetype

    stock = Stock(
        pr_name=name,
        pr_price=price,
        pr_category=category,
        pr_img=image_data,
        pr_img_mimetype=image_mimetype,
        seller_id=current_user().id,
    )

    try:
        db.session.add(stock)
        db.session.commit()
        flash("Product added successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("The product could not be saved. Please try again.", "error")

    return redirect(url_for("add_products_page"))


@app.route("/product-image/<int:product_id>")
@login_required
def product_image(product_id):
    product = db.session.get(Stock, product_id)
    if product is None or not product.pr_img:
        return "", 404
    return Response(
        product.pr_img,
        mimetype=product.pr_img_mimetype or "application/octet-stream",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    if current_user().role != "buyer":
        flash("Only buyer accounts can add products to a cart.", "error")
        return redirect(url_for("dashboard"))

    product = db.session.get(Stock, product_id)
    if product is None:
        flash("That product could not be found.", "error")
        return redirect(url_for("dashboard"))

    cart = session.get("cart", {})
    product_key = str(product_id)
    cart[product_key] = cart.get(product_key, 0) + 1
    session["cart"] = cart
    flash(f"{product.pr_name} added to your cart.", "success")
    return redirect(url_for("dashboard"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
