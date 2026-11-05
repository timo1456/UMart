from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text(collation="NOCASE"), nullable=False, unique=True)
    email = db.Column(db.Text(collation="NOCASE"), nullable=False, unique=True)
    role = db.Column(db.Text(collation="NOCASE"), nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pr_name = db.Column(db.String(100), nullable=False)
    pr_price = db.Column(db.Integer, nullable=False)
    pr_img = db.Column(db.LargeBinary, nullable=True)
    pr_category = db.Column(db.String(100), nullable=False)
