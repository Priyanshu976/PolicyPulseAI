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

@app.route("/init-db")
def init_db():
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

    return "Database initialized successfully!"


if __name__ == "__main__":
    app.run()
