from flask import Flask, request, render_template, jsonify, session,flash
import os
from werkzeug.utils import secure_filename
from utils.embedder import embed_text, get_gemini_response
from utils.chroma_handler import store_chunks, retrieve_chunks

from uuid import uuid4
from flask_cors import CORS
from datetime import timedelta
import markdown
import fitz  # PyMuPDF
from PIL import Image
import io
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'



app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app, supports_credentials=True)

app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False
)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.permanent_session_lifetime = timedelta(days=7)

users = {} 
chat_histories = {}

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            return "Email and password required", 400
        if email in users:
            return "User already exists", 400
        users[email] = password
        session['user'] = email
        session.permanent = True
        return '''
        <script>
            alert("Signup successful!");
            window.location.href = "/login";
        </script>
        '''
        # return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email not in users or users[email] != password:
            # return "Invalid email or password", 401
            return '''
            <script>
                alert("Invalid email or password!");
                window.location.href = "/login";
            </script>
            ''' , 401
        session['user'] = email
        session.permanent = True
        return '''
        <script>
            alert("Login successful!");
            window.location.href = "/";
        </script>
        '''
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return '''
        <script>
            alert("User Logout!");
            window.location.href = "/";
        </script>
        '''
    
    # return redirect('/')


@app.route('/check-auth', methods=['GET'])
def check_auth():
    user = session.get('user')
    if user:
        return jsonify({'loggedIn': True, 'user': user})
    return jsonify({'loggedIn': False})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user' not in session:
        return "Unauthorized, login first", 401

    file = request.files.get('file')
    if not file:
        return "No file uploaded", 400

    filename = secure_filename(file.filename)
    allowed_extensions = {'pdf', 'txt'}
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        # return "Unsupported file format. Please upload only PDF or TXT files.", 400
        return '''
            <script>
                alert("Unsupported file format. Please upload only PDF or TXT files.");
                window.location.href = "/";
            </script>
            ''',400
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    if filename.lower().endswith('.pdf'):
        text = extract_text(filepath)
    else: 
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    chunks = split_into_chunks(text)
    session_id = str(uuid4())
    embeddings = embed_text(chunks)
    store_chunks(session_id, chunks, embeddings)
    session['session_id'] = session_id
    # print("Session ID set:", session_id) 
    return '''
        <script>
            alert("Login successful!");
            window.location.href = "/";
        </script>
        '''


from flask import redirect
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user' not in session:
        return redirect('/login')

    session_id = session.get('session_id')
    if not session_id:
        # flash("Please upload a file first.")
        # return redirect('/')
        return '''
            <script>
                alert("Please upload a file first.");
                window.location.href = "/";
            </script>
            '''

    if request.method == 'POST':
        query = request.form.get('message')
        if not query:
            # flash("Please enter a question.")
            # return redirect('/')
            return '''
                <script>
                    alert("PPlease enter a question.");
                    window.location.href = "/";
                </script>
                '''
        

        if session_id not in chat_histories:
            chat_histories[session_id] = []

        chat_histories[session_id].append({"role": "user", "content": query})

        query_embedding = embed_text([query])[0]
        relevant_chunks = retrieve_chunks(session_id, query_embedding, top_k=3)
        answer = get_gemini_response(query, relevant_chunks)
        print(answer)
        html_answer = markdown.markdown(answer)  # Convert markdown to HTML
        chat_histories[session_id].append({"role": "bot", "content": html_answer})

        return render_template("index.html", response=html_answer, chat_history=chat_histories[session_id], user=session.get('user'))


    return render_template("index.html", user=session.get('user'))






def extract_text(filepath):
    doc = fitz.open(filepath)
    full_text = ""

    for page in doc:
        # Try to extract digital text
        text = page.get_text().strip()
        
        if text:
            full_text += text + "\n"
        else:
            # If digital text not found, do OCR
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")  # Convert to image bytes
            img = Image.open(io.BytesIO(img_data))
            ocr_text = pytesseract.image_to_string(img)
            full_text += ocr_text + "\n"
    
    return full_text


def split_into_chunks(text, chunk_size=1400):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

print(users)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)



