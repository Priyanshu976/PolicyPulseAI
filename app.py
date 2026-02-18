import os
from flask import Flask
from dotenv import load_dotenv
import psycopg2

load_dotenv()

app = Flask(__name__)
app.secret_key = "super_secret_key"

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@app.route("/")
def home():
    return "Policy Pulse AI Clean Version Running!"

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return f"Database connected successfully! Result: {result}"
    except Exception as e:
        return f"Database connection failed: {e}"


if __name__ == "__main__":
    app.run()
