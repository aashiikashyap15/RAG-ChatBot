import os
import uuid
import time
from functools import wraps

from flask import (
    Flask, request, jsonify,
    render_template, session, redirect, url_for
)
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from utils.chroma_handler import (
    init_db, store_chunks, search_chunks,
    get_all_sources, get_user, create_user
)
from utils.loader import load_document
from utils.chunker import split_into_chunks
from utils.embedder import batch_embed, get_query_embedding
from utils.memory import get_history, add_message, clear_history
from utils.gemini_client import build_prompt, get_response

# ── App Setup ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
CORS(app)

bcrypt = Bcrypt(app)

UPLOAD_FOLDER = "./uploads"
ALLOWED_EXTENSIONS = {"pdf", "txt"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()


# ── Helpers ────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Auth Routes ────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or len(username) < 3:
            return render_template(
                "signup.html",
                error="Username must be at least 3 characters."
            )

        if get_user(username):
            return render_template(
                "signup.html",
                error="Username already taken."
            )

        hashed = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        if create_user(username, hashed):
            return redirect(url_for("login"))
        else:
            return render_template(
                "signup.html",
                error="Registration failed. Try again."
            )

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_user(username)
        if user and bcrypt.check_password_hash(
            user.password_hash, password
        ):
            session["user"] = username
            session["session_id"] = str(uuid.uuid4())
            return redirect(url_for("index"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Main Page ──────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    sources = get_all_sources()
    return render_template(
        "index.html",
        username=session["user"],
        sources=sources
    )


# ── Upload ─────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file in request"}), 400

    file = request.files["file"]

    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {"error": "Only PDF and TXT files allowed"}
        ), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        start = time.time()

        print(f"📄 Loading: {filename}")
        text = load_document(filepath)

        if not text.strip():
            return jsonify(
                {"error": "Document appears empty"}
            ), 400

        print(f"✂️  Chunking...")
        chunks = split_into_chunks(
            text, chunk_size=200, source_name=filename
        )

        print(f"🧠 Embedding {len(chunks)} chunks...")
        chunks = batch_embed(chunks)

        print(f"💾 Storing in PostgreSQL...")
        store_chunks(chunks)

        elapsed = round(time.time() - start, 2)
        return jsonify({
            "success": True,
            "filename": filename,
            "chunks_stored": len(chunks),
            "processing_time_sec": elapsed
        })

    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# ── Chat ───────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    query = data.get("query", "").strip()[:800]
    if not query:
        return jsonify({"error": "Empty query"}), 400

    session_id = session.get("session_id", "default")

    try:
        start = time.time()

        q_embed = get_query_embedding(query)
        chunks = search_chunks(q_embed, top_k=5)

        if not chunks:
            return jsonify({
                "answer": (
                    "No documents found. "
                    "Please upload a document first."
                ),
                "sources": [],
                "debug": {}
            })

        history = get_history(session_id)
        prompt = build_prompt(query, chunks, history)
        answer = get_response(prompt)

        add_message(session_id, "user", query)
        add_message(session_id, "assistant", answer)

        elapsed = round(time.time() - start, 3)

        sources = [
            {
                "source": c["metadata"]["source"],
                "page": c["metadata"]["page"],
                "chunk_index": c["metadata"]["chunk_index"],
                "preview": c["text"][:180] + "..."
            }
            for c in chunks
        ]

        return jsonify({
            "answer": answer,
            "sources": sources,
            "debug": {
                "chunks_retrieved": len(chunks),
                "query_time_sec": elapsed,
                "session_id": session_id[:8] + "..."
            }
        })

    except Exception as e:
        print(f"❌ Chat error: {e}")
        return jsonify({"error": str(e)}), 500


# ── Clear Chat ─────────────────────────────────────────────
@app.route("/clear", methods=["POST"])
@login_required
def clear():
    sid = session.get("session_id", "default")
    clear_history(sid)
    session["session_id"] = str(uuid.uuid4())
    return jsonify({"success": True})


# ── Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
