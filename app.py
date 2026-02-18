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

if __name__ == "__main__":
    app.run(debug=True)
