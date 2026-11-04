from pathlib import Path
import sqlite3

from flask import Flask, render_template

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "store.db"

app = Flask(__name__)


def get_db_connection():
    """Open a connection to the project's SQLite database."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    return render_template("index.html")





if __name__ == "__main__":
    app.run(debug=True)
