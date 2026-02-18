import os
from flask import Flask, request, redirect, render_template, session
from dotenv import load_dotenv
import psycopg2
import PyPDF2
import re
from collections import Counter

STOPWORDS = {
    "the", "is", "in", "and", "to", "of", "for", "on", "with",
    "as", "by", "an", "be", "this", "that", "are", "from",
    "at", "or", "it", "was", "will", "has", "have"
}



load_dotenv()

app = Flask(__name__)
app.secret_key = "super_secret_key"

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    return text

def generate_summary(text, num_sentences=5):
    # Clean text
    text = re.sub(r'\s+', ' ', text)

    # Split into sentences
    sentences = re.split(r'(?<=[.!?]) +', text)

    if len(sentences) <= num_sentences:
        return text

    # Word frequency
    words = re.findall(r'\w+', text.lower())
    word_freq = Counter(words)

    sentence_scores = {}

    for sentence in sentences:
        for word in re.findall(r'\w+', sentence.lower()):
            if word in word_freq:
                sentence_scores[sentence] = sentence_scores.get(sentence, 0) + word_freq[word]

    # Sort sentences by score
    ranked_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)

    summary_sentences = ranked_sentences[:num_sentences]

    summary = " ".join(summary_sentences)

    return summary

def analyze_sentiment(text):
    positive_words = {
        "growth", "benefit", "improve", "support", "development",
        "increase", "success", "empower", "opportunity", "progress"
    }

    negative_words = {
        "risk", "decline", "problem", "crisis", "loss",
        "decrease", "burden", "failure", "issue", "threat"
    }

    text = text.lower()
    words = re.findall(r'\w+', text)

    positive_score = sum(1 for word in words if word in positive_words)
    negative_score = sum(1 for word in words if word in negative_words)

    if positive_score > negative_score:
        return "Positive"
    elif negative_score > positive_score:
        return "Negative"
    else:
        return "Neutral"

def extract_keywords(text, top_n=8):
    words = re.findall(r'\w+', text.lower())

    filtered_words = [
        word for word in words
        if word not in STOPWORDS and len(word) > 3
    ]

    word_freq = Counter(filtered_words)

    most_common = word_freq.most_common(top_n)

    keywords = [word for word, freq in most_common]

    return ", ".join(keywords)


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
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("ALTER TABLE policies ADD COLUMN IF NOT EXISTS keywords TEXT;")

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
            "SELECT id, password, role FROM users WHERE email=%s",
            (email,)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["role"] = user[2]
            return redirect("/dashboard")

        return "Invalid credentials."

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch user policies
    cur.execute(
        "SELECT title, summary, created_at, sentiment, keywords FROM policies WHERE user_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    policies = cur.fetchall()

    # Total policies
    total_policies = len(policies)

    # Sentiment counts
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    all_keywords = []

    for policy in policies:
        raw_sentiment = policy[3]

        if raw_sentiment:
            sentiment = raw_sentiment.capitalize()
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1

        if policy[4]:
            all_keywords.extend(policy[4].split(", "))

    # Most common keywords
    keyword_freq = Counter(all_keywords)
    top_keywords = keyword_freq.most_common(5)

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        policies=policies,
        total_policies=total_policies,
        sentiment_counts=sentiment_counts,
        top_keywords=top_keywords
    )


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

@app.route("/upload-policy", methods=["GET", "POST"])
def upload_policy():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        pdf_file = request.files["pdf"]

        if pdf_file.filename == "":
            return "No file selected."

        try:
            text = extract_text_from_pdf(pdf_file)
            summary = generate_summary(text)
            sentiment = analyze_sentiment(summary)
            keywords = extract_keywords(summary)


            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO policies (user_id, title, summary, sentiment, keywords) VALUES (%s, %s, %s, %s, %s)",
                (session["user_id"], title, summary, sentiment, keywords)

            )

            conn.commit()
            cur.close()
            conn.close()

            return f"<h3>Summary:</h3><p>{summary}</p><br><a href='/dashboard'>Back to Dashboard</a>"

        except Exception as e:
            return f"Error processing PDF: {e}"

    return render_template("upload_policy.html")

@app.route("/admin")
def admin_panel():
    if "user_id" not in session:
        return "Access Denied"

    if session.get("role") != "admin":
        return "Access Denied"

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM policies")
    total_policies = cur.fetchone()[0]
    cur.execute("SELECT sentiment, COUNT(*) FROM policies GROUP BY sentiment")
    sentiment_data = cur.fetchall()
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for sentiment, count in sentiment_data:
        if sentiment:
            formatted = sentiment.capitalize()
            if formatted in sentiment_counts:
                sentiment_counts[formatted] = count
    cur.execute("SELECT keywords FROM policies WHERE keywords IS NOT NULL")
    keyword_rows = cur.fetchall()
    all_keywords = []
    for row in keyword_rows:
        if row[0]:
            all_keywords.extend(row[0].split(", "))
    keyword_freq = Counter(all_keywords)
    top_keywords = keyword_freq.most_common(5)


    cur.close()
    conn.close()

    return render_template(
    "admin_dashboard.html",
    total_users=total_users,
    total_policies=total_policies,
    sentiment_counts=sentiment_counts,
    top_keywords=top_keywords
)


import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

@app.route("/scheme-advisor", methods=["GET", "POST"])
def scheme_advisor():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        age = request.form["age"]
        gender = request.form["gender"]
        income = request.form["income"]
        occupation = request.form["occupation"]
        state = request.form["state"]
        area_type = request.form["area_type"]
        need = request.form["need"]

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
            You are an AI Government Scheme Advisor for Indian citizens.

            User Profile:
            Age: {age}
            Gender: {gender}
            Monthly Income: {income}
            Occupation: {occupation}
            State: {state}
            Area Type: {area_type}
            Need: {need}

            Provide:
            1. 3-5 relevant government schemes
            2. Key benefits
            3. Eligibility criteria
            4. How to apply
            5. Official website link (if possible)

            Keep explanation simple and structured.
            """

            response = model.generate_content(prompt)
            advice = response.text

            return render_template("scheme_result.html", advice=advice)

        except Exception as e:
            return f"Error: {e}"

    return render_template("scheme_form.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")




if __name__ == "__main__":
    app.run()
