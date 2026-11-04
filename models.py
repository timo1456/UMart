from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text(collation="NOCASE"), nullable=False, unique=True)
    email = db.Column(db.Text(collation="NOCASE"), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
