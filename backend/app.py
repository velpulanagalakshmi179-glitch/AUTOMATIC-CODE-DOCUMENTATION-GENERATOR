"""
╔══════════════════════════════════════════════════════════════╗
║   ⚡ AUTOMATIC CODE DOCUMENTATION GENERATOR                  ║
║   Backend: Flask + Groq AI (LLaMA3-70B)                     ║
║   Pure REST API — Frontend is separate                       ║
║                                                              ║
║   Install:  pip install -r requirements.txt                  ║
║   Run:      python app.py                                    ║
║   API Base: http://localhost:5000/api/...                    ║
╚══════════════════════════════════════════════════════════════╝
"""

# ════════════════════════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════════════════════════
import os
import ast
import difflib
import subprocess
import tempfile
import textwrap
import re
import sqlite3, hashlib, secrets
from io import BytesIO
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS                    # allows frontend to call this API
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image as RLImage
)

# ════════════════════════════════════════════════════════════════
# LOAD .env  →  GROQ API KEY
# ════════════════════════════════════════════════════════════════
load_dotenv()   # reads .env file from backend/ folder

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "\n\n  ❌  GROQ_API_KEY not found!\n"
        "  Create a .env file in the backend/ folder:\n"
        "  GROQ_API_KEY=your_key_here\n"
        "  Get a free key at: https://console.groq.com\n"
    )

# ════════════════════════════════════════════════════════════════
# APP SETUP
# ════════════════════════════════════════════════════════════════
app = Flask(__name__)
app.secret_key = "codedoc_secret_key_2026_navya"
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Allow frontend to call this API with credentials
CORS(app, 
     resources={r"/api/*": {"origins": ["http://127.0.0.1:5501", 
                                         "http://localhost:5501"]}},
     supports_credentials=True,
     allow_headers=["Content-Type"],
     methods=["GET", "POST", "OPTIONS"])

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024   # 10 MB

groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL  = "llama-3.3-70b-versatile"


# ════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ════════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        code_snippet TEXT,
        result_preview TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()


# ════════════════════════════════════════════════════════════════
# HELPER — Call Groq AI
# ════════════════════════════════════════════════════════════════
def call_groq(system_prompt: str, user_content: str, max_tokens: int = 2048) -> str:
    """Send a prompt to Groq LLaMA3-70B and return the text response."""
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
    )
    return response.choices[0].message.content.strip()


# ════════════════════════════════════════════════════════════════
# HELPER — Render Mermaid → PNG  (needs mmdc CLI, optional)
# ════════════════════════════════════════════════════════════════
def render_mermaid(mermaid_code: str) -> bytes | None:
    """
    Convert Mermaid syntax to PNG using the mmdc CLI.
    Install: npm install -g @mermaid-js/mermaid-cli
    Returns PNG bytes, or None if mmdc is not installed.
    """
    mmd_path = png_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mmd", delete=False, mode="w") as f:
            f.write(mermaid_code)
            mmd_path = f.name
        png_path = mmd_path.replace(".mmd", ".png")
        result = subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", png_path, "-b", "transparent"],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(png_path):
            with open(png_path, "rb") as img:
                return img.read()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    finally:
        for p in [mmd_path, png_path]:
            if p and os.path.exists(p):
                try: os.remove(p)
                except OSError: pass
    return None


# ════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ════════════════════════════════════════════════════════════════
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(force=True)
    name = data.get("name","").strip()
    email = data.get("email","").strip().lower()
    username = data.get("username","").strip().lower()
    password = data.get("password","").strip()
    if not name or not email or not username or not password:
        return jsonify({"error": "All fields required"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email format"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password too short"}), 400
    hashed = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    if c.fetchone():
        conn.close()
        return jsonify({"error": "Email already registered! Please login."}), 400
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({"error": "Username already taken! Try another."}), 400
    try:
        c.execute("INSERT INTO users (name,email,username,password,created_at) VALUES (?,?,?,?,?)",
                  (name, email, username, hashed, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"message": "Account created successfully"})
    except sqlite3.IntegrityError as e:
        conn.close()
        if "email" in str(e):
            return jsonify({"error": "Email already registered! Please login."}), 400
        else:
            return jsonify({"error": "Username already taken! Try another."}), 400

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(force=True)
    identifier = data.get("username","").strip().lower()
    password = data.get("password","").strip()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, name, username, email FROM users WHERE (username=? OR email=?) AND password=?",
              (identifier, identifier, hashed))
    user = c.fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "Invalid username/email or password!"}), 401
    session['user_id'] = user[0]
    session['user_name'] = user[1]
    session['username'] = user[2]
    session.permanent = True
    return jsonify({"message": "Login successful", "name": user[1], "username": user[2], "email": user[3]})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"name": session['user_name'], "username": session['username']})

@app.route("/api/auth/change-password", methods=["POST"])
def auth_change_password():
    data = request.get_json(force=True)
    username = data.get("username","").strip().lower()
    current_password = data.get("current_password","").strip()
    new_password = data.get("new_password","").strip()
    if not username or not current_password or not new_password:
        return jsonify({"error": "All fields required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password too short"}), 400
    current_hashed = hashlib.sha256(current_password.encode()).hexdigest()
    new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?",
              (username, current_hashed))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "Current password is wrong!"}), 401
    c.execute("UPDATE users SET password=? WHERE username=?",
              (new_hashed, username))
    conn.commit()
    conn.close()
    return jsonify({"message": "Password changed successfully"})


@app.route("/api/auth/update-profile", methods=["POST"])
def auth_update_profile():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    username = data.get("username", "").strip().lower()
    email = data.get("email", "").strip().lower()
    old_username = data.get("old_username", "").strip().lower()
    
    if not name or not username or not email:
        return jsonify({"error": "All fields required"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email format"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check if new email already exists (if different from old email)
    c.execute("SELECT id FROM users WHERE email=? AND username!=?", (email, old_username))
    if c.fetchone():
        conn.close()
        return jsonify({"error": "Email already registered by another user!"}), 400
    
    # Check if new username already exists (if different from old username)
    if username != old_username:
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        if c.fetchone():
            conn.close()
            return jsonify({"error": "Username already taken!"}), 400
    
    # Update profile in database
    c.execute("UPDATE users SET name=?, username=?, email=? WHERE username=?",
              (name, username, email, old_username))
    conn.commit()
    conn.close()
    
    # Update session data
    session['user_name'] = name
    session['username'] = username
    
    return jsonify({"message": "Profile updated successfully"})


# ════════════════════════════════════════════════════════════════
# HISTORY ROUTES
# ════════════════════════════════════════════════════════════════
@app.route("/api/history/save", methods=["POST"])
def history_save():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json(force=True)
    action = data.get("action","")
    code_snippet = data.get("code","")[:200]
    result_preview = data.get("result","")[:300]
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO history (user_id,action,code_snippet,result_preview,created_at) VALUES (?,?,?,?,?)",
              (session['user_id'], action, code_snippet, result_preview, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"message": "Saved"})

@app.route("/api/history/get", methods=["GET"])
def history_get():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id,action,code_snippet,result_preview,created_at FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
              (session['user_id'],))
    rows = c.fetchall()
    conn.close()
    items = [{"id":r[0],"action":r[1],"code":r[2],"preview":r[3],"time":r[4]} for r in rows]
    return jsonify({"history": items})


# ════════════════════════════════════════════════════════════════
# HELPER — Extract Mermaid block from Groq response
# ════════════════════════════════════════════════════════════════
def extract_mermaid(text: str) -> str:
    m = re.search(r"```(?:mermaid)?\s*(flowchart[\s\S]+?)```", text, re.IGNORECASE)
    if m: return m.group(1).strip()
    m = re.search(r"(flowchart\s+\w+[\s\S]+)", text, re.IGNORECASE)
    if m: return m.group(1).strip()
    return text.strip()


# ════════════════════════════════════════════════════════════════
# HELPER — Safe filename for downloads
# ════════════════════════════════════════════════════════════════
def safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)[:64]


# ════════════════════════════════════════════════════════════════
# API 0 — BUG FINDER
# ════════════════════════════════════════════════════════════════
@app.route("/api/bugfinder", methods=["POST"])
def api_bugfinder():
    code = request.get_json(force=True).get("code","").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400
    system = textwrap.dedent("""
        You are an expert code reviewer and debugger.
        Analyze the given code in ANY programming language.
        Find ALL bugs, errors, warnings and improvements.
        Format your response EXACTLY like this:
        🐛 BUGS FOUND:
        1. [Line X] Description of bug and how to fix it
        ⚠️ WARNINGS:
        1. Description of warning
        💡 SUGGESTIONS:
        1. Improvement suggestion
        ✅ FIXED CODE:
        (provide the corrected version of the code)
        Be specific, clear and beginner-friendly.
        If no bugs found say: No bugs found! Code looks good.
    """).strip()
    try:
        result = call_groq(system, code, 2048)
        bugs = result.lower().count("bug")
        warnings = result.lower().count("warning")
        suggestions = result.lower().count("suggestion")
        return jsonify({
            "report": result,
            "bugs": min(bugs, 20),
            "warnings": min(warnings, 20),
            "suggestions": min(suggestions, 20)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API 1 — EXTRACT FUNCTIONS  (Python AST + Groq for other languages)
# ════════════════════════════════════════════════════════════════
@app.route("/api/extract", methods=["POST"])
def api_extract():
    """
    Extract function/method definitions from code in any programming language.
    Uses Python AST for Python code, Groq AI for other languages.
    Input : { code: str }
    Output: { functions: [ { name, args, line, is_async, docstring } ], count: int }
    """
    code = request.get_json(force=True).get("code", "").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Try Python AST first
    try:
        tree = ast.parse(code)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name":      node.name,
                    "args":      [a.arg for a in node.args.args],
                    "line":      node.lineno,
                    "is_async":  isinstance(node, ast.AsyncFunctionDef),
                    "docstring": ast.get_docstring(node) or "",
                })
        if functions:
            return jsonify({"functions": functions, "count": len(functions)})
    except (SyntaxError, ValueError):
        pass

    # Fallback — use Groq for any language
    system = textwrap.dedent("""
        You are a code analyzer. Extract all functions/methods from the given code regardless of programming language.
        Return a JSON array only, no explanation, in this exact format:
        [{"name": "functionName", "args": ["arg1", "arg2"], "line": 1}]
    """).strip()
    try:
        result = call_groq(system, code, 1024)
        import json
        result = result.strip().replace("```json","").replace("```","")
        functions = json.loads(result)
        return jsonify({"functions": functions, "count": len(functions)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API 2 — GENERATE DOCUMENTATION  (Groq AI)
# ════════════════════════════════════════════════════════════════
@app.route("/api/document", methods=["POST"])
def api_document():
    """
    Generate professional AI documentation for all functions.
    Input : { code: str }
    Output: { documentation: str }
    """
    code = request.get_json(force=True).get("code", "").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400

    system = textwrap.dedent("""
        You are a professional code documentation writer.
        Analyze the given code in ANY programming language (Python, Java, JavaScript, C++, Go, Rust, etc).
        For each function/method generate:
        1. A clear description (Parameters, Returns, Raises sections)
        2. A short usage example
        Format with markdown headings per function. Be concise but complete.
    """).strip()

    try:
        doc = call_groq(system, f"Document this code:\n\n```\n{code}\n```")
        return jsonify({"documentation": doc})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API 3 — EXPLAIN + FLOWCHART  (Groq AI + Mermaid)
# ════════════════════════════════════════════════════════════════
@app.route("/api/explain", methods=["POST"])
def api_explain():
    """
    Step-by-step explanation + auto-generated Mermaid flowchart.
    Input : { code: str }
    Output: { explanation: str, mermaid_code: str, flowchart_b64?: str }
    """
    code = request.get_json(force=True).get("code", "").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400

    explain_sys = textwrap.dedent("""
        You are a coding teacher explaining code to beginners.
        The code can be in ANY programming language.
        Detect the language first, then break the code into numbered steps.
        Describe WHAT each part does and WHY. Keep it simple and friendly.
    """).strip()

    chart_sys = textwrap.dedent("""
        Generate a valid Mermaid.js flowchart TD for the given code.
        The code can be in ANY programming language.
        Rules:
        - Start with: flowchart TD
        - Use only simple alphanumeric node IDs like A, B, C
        - Node labels inside square brackets like A[label]
        - Decisions use curly braces like C{condition}
        - NO special characters in labels, NO quotes, NO markdown
        - Keep it simple — max 10 nodes
        - Return ONLY the Mermaid code, nothing else
    """).strip()

    try:
        explanation  = call_groq(explain_sys, f"Explain step by step:\n\n```\n{code}\n```")
        mermaid_raw  = call_groq(chart_sys,   f"Flowchart for:\n\n```\n{code}\n```", 1024)
        mermaid_code = extract_mermaid(mermaid_raw)

        # Try server-side render (requires mmdc) — return as base64 so frontend can display it
        png = render_mermaid(mermaid_code)
        if png:
            import base64
            b64 = base64.b64encode(png).decode("utf-8")
            return jsonify({
                "explanation":   explanation,
                "mermaid_code":  mermaid_code,
                "flowchart_b64": b64,           # frontend uses this as <img src="data:image/png;base64,...">
            })

        # Fallback — send raw Mermaid for browser rendering via Mermaid CDN
        return jsonify({
            "explanation":  explanation,
            "mermaid_code": mermaid_code,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API 4 — COMPLEXITY ANALYSIS  (Groq AI)
# ════════════════════════════════════════════════════════════════
@app.route("/api/complexity", methods=["POST"])
def api_complexity():
    """
    Analyze time and space complexity (Big-O notation) for all functions.
    Input : { code: str }
    Output: { complexity: str }
    """
    code = request.get_json(force=True).get("code", "").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400

    system = textwrap.dedent("""
        You are an algorithm complexity analyst.
        Analyze code written in ANY programming language (Python, Java, C++, JavaScript, Go, Rust, etc).
        For each function/method provide:
        1. Time Complexity (Big-O) with explanation
        2. Space Complexity (Big-O) with explanation
        3. Possible optimizations
        Use function names as section headers.
    """).strip()

    try:
        result = call_groq(system, f"Analyze complexity:\n\n```\n{code}\n```")
        return jsonify({"complexity": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API 5 — PLAGIARISM DETECTION  (difflib)
# ════════════════════════════════════════════════════════════════
@app.route("/api/plagiarism", methods=["POST"])
def api_plagiarism():
    """
    Compare two code files using difflib.SequenceMatcher.
    Input : { code1: str, code2: str }
    Output: { similarity: float, verdict: str, details: str }
    """
    data  = request.get_json(force=True)
    code1 = data.get("code1", "").strip()
    code2 = data.get("code2", "").strip()

    if not code1 or not code2:
        return jsonify({"error": "Both code files are required"}), 400

    def normalize(c: str) -> str:
        lines = []
        for l in c.splitlines():
            stripped = l.strip()
            # Remove single line comments for any language
            stripped = re.sub(r'//.*|#.*|--.*', '', stripped)
            if stripped:
                lines.append(stripped)
        return "\n".join(lines)

    ratio      = difflib.SequenceMatcher(None, normalize(code1), normalize(code2)).ratio()
    similarity = round(ratio * 100, 2)

    if similarity < 40:
        verdict = "Low"
        msg     = "Files appear largely different."
    elif similarity < 70:
        verdict = "Moderate"
        msg     = "Moderate overlap — manual review recommended."
    else:
        verdict = "High"
        msg     = "High similarity — possible plagiarism!"

    diff_lines   = list(difflib.unified_diff(
        code1.splitlines(), code2.splitlines(),
        fromfile="File 1", tofile="File 2", lineterm=""
    ))
    diff_preview = "\n".join(diff_lines[:60])
    details = (
        f"Similarity Score : {similarity}%\n"
        f"Verdict          : {verdict} — {msg}\n\n"
        f"--- Diff Preview ---\n{diff_preview or '(files are identical)'}"
    )

    return jsonify({"similarity": similarity, "verdict": verdict, "details": details})


# ════════════════════════════════════════════════════════════════
# API 6 — TRANSLATE DOCUMENTATION  (Groq AI)
# ════════════════════════════════════════════════════════════════
@app.route("/api/translate", methods=["POST"])
def api_translate():
    """
    Translate documentation text into a target language using Groq AI.
    Input : { documentation: str, language: str }
    Output: { translated: str, language: str }
    """
    data          = request.get_json(force=True)
    documentation = data.get("documentation", "").strip()
    language      = data.get("language", "Hindi")

    if not documentation:
        return jsonify({"error": "No documentation provided"}), 400

    supported = ["Hindi", "Arabic", "French", "Spanish", "Urdu",
                 "Chinese", "German", "Portuguese", "Japanese", "Russian"]

    if language not in supported:
        return jsonify({"error": f"Unsupported language. Choose from: {supported}"}), 400

    system = textwrap.dedent(f"""
        You are a professional technical translator.
        Translate the following code documentation into {language}.
        The documentation may refer to ANY programming language.
        Keep all code terms, function names, and technical keywords in English.
        Preserve all formatting. Output ONLY the translated text.
    """).strip()

    try:
        translated = call_groq(system, documentation, max_tokens=3000)
        return jsonify({"translated": translated, "language": language})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API 7a — EXPORT PDF  (ReportLab)
# ════════════════════════════════════════════════════════════════
@app.route("/api/export/pdf", methods=["POST"])
def api_export_pdf():
    """
    Generate a formatted PDF using ReportLab.
    Input : { title: str, content: str }
    Output: PDF file download
    """
    data    = request.get_json(force=True)
    title   = data.get("title", "Code Documentation")
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "No content to export"}), 400

    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=0.75*inch, leftMargin=0.75*inch,
                               topMargin=0.75*inch,   bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story  = []

    t_sty = ParagraphStyle("T", parent=styles["Title"],  fontSize=22,
                            textColor=colors.HexColor("#7c3aed"), spaceAfter=6)
    s_sty = ParagraphStyle("S", parent=styles["Normal"], fontSize=10,
                            textColor=colors.HexColor("#64748b"), spaceAfter=18)
    b_sty = ParagraphStyle("B", parent=styles["Normal"], fontSize=10,
                            leading=16, spaceAfter=8)
    c_sty = ParagraphStyle("C", parent=styles["Code"],   fontSize=9,
                            leading=14, backColor=colors.HexColor("#f1f5f9"),
                            leftIndent=12, rightIndent=12, borderPad=8, spaceAfter=10)

    story += [
        Paragraph(title, t_sty),
        Paragraph("Generated by Code Doc Generator • Powered by Groq AI", s_sty),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#7c3aed")),
        Spacer(1, 0.2*inch),
    ]

    for line in content.splitlines():
        if not line.strip():
            story.append(Spacer(1, 0.08*inch)); continue
        if   line.startswith("### "): story.append(Paragraph(line[4:], styles["Heading3"]))
        elif line.startswith("## "):  story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("# "):   story.append(Paragraph(line[2:], styles["Heading1"]))
        elif line.startswith("    ") or line.startswith("\t"):
            story.append(Paragraph(line.strip(), c_sty))
        else:
            safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            story.append(Paragraph(safe, b_sty))

    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{safe_filename(title)}.pdf")


# ════════════════════════════════════════════════════════════════
# API 7b — EXPORT TXT
# ════════════════════════════════════════════════════════════════
@app.route("/api/export/txt", methods=["POST"])
def api_export_txt():
    """Export documentation as plain text (.txt)."""
    data    = request.get_json(force=True)
    title   = data.get("title", "Documentation")
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "No content to export"}), 400

    buf = BytesIO(f"{title}\n{'=' * len(title)}\n\n{content}\n".encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="text/plain", as_attachment=True,
                     download_name=f"{safe_filename(title)}.txt")


# ════════════════════════════════════════════════════════════════
# API 7c — EXPORT MARKDOWN
# ════════════════════════════════════════════════════════════════
@app.route("/api/export/markdown", methods=["POST"])
def api_export_markdown():
    """Export documentation as a Markdown (.md) file."""
    data    = request.get_json(force=True)
    title   = data.get("title", "Documentation")
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "No content to export"}), 400

    buf = BytesIO(f"# {title}\n\n{content}\n".encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="text/markdown", as_attachment=True,
                     download_name=f"{safe_filename(title)}.md")


# ════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ════════════════════════════════════════════════════════════════
@app.errorhandler(400)
def bad_request(e):   return jsonify({"error": "Bad request",           "details": str(e)}), 400

@app.errorhandler(404)
def not_found(e):     return jsonify({"error": "Endpoint not found"}),            404

@app.errorhandler(500)
def server_error(e):  return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# RUN
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("⚡ Code Doc Generator — Backend API running")
    print("   API Base URL: http://localhost:5000/api/")
    print("   Open your frontend/index.html in a browser")
    app.run(debug=True, host="0.0.0.0", port=5000)