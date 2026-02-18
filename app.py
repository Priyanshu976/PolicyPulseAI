import os
from flask import Flask, request, redirect, render_template, session
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
    
    
@app.route("/init-db")
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(120) UNIQUE NOT NULL,
                password VARCHAR(200) NOT NULL,
                role VARCHAR(20) DEFAULT 'user'
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                title VARCHAR(200),
                summary TEXT,
                sentiment VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cur.close()
        conn.close()

        return "Tables created successfully!"
    except Exception as e:
        return f"Error creating tables: {e}"

from werkzeug.security import generate_password_hash

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"Error: {e}"

        cur.close()
        conn.close()

        return "User registered successfully!"

    return render_template("register.html")

from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, password FROM users WHERE email=%s",
            (email,)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect("/dashboard")

        return "Invalid credentials."

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT title, summary, created_at FROM policies WHERE user_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )

    policies = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html", policies=policies)


@app.route("/add-policy", methods=["GET", "POST"])
def add_policy():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        summary = request.form["summary"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO policies (user_id, title, summary, sentiment) VALUES (%s, %s, %s, %s)",
            (session["user_id"], title, summary, "neutral")
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_policy.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")




if __name__ == "__main__":
    app.run()
