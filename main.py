import streamlit as st
import sqlite3
import hashlib
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import google.generativeai as genai
import os
from dotenv import load_dotenv
from streamlit_option_menu import option_menu
from pypdf import PdfReader

# load key
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# db and files
DB_NAME = "IntervuAI_bot.db"
UPLOAD_DIR = "user_uploaded_files"

# init db
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            date_of_birth TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS files(
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            file_path TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)
    print("db ready")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def sign_up(fn, ln, dob, email, pw):
    with sqlite3.connect(DB_NAME) as conn:
        try:
            conn.execute("INSERT INTO users(first_name,last_name,date_of_birth,email,password) VALUES(?,?,?,?,?)",
                         (fn, ln, str(dob), email, hash_pw(pw)))
            conn.commit()
            return True, "Account created"
        except sqlite3.IntegrityError:
            return False, "Email already exists"

def login(email, pw):
    with sqlite3.connect(DB_NAME) as conn:
        u = conn.execute("SELECT user_id,first_name,last_name FROM users WHERE email=? AND password=?",
                         (email, hash_pw(pw))).fetchone()
        return u if u else None

def save_file(uid, fname, fpath):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO files(user_id,file_name,file_path) VALUES(?,?,?)", (uid, fname, fpath))
        conn.commit()

def get_user_files(uid):
    with sqlite3.connect(DB_NAME) as conn:
        f = conn.execute("SELECT file_name,file_path FROM files WHERE user_id=?", (uid,)).fetchall()
        return f

def delete_file(uid, fname):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM files WHERE user_id=? AND file_name=?", (uid, fname))
        conn.commit()

init_db()

# embeddings + helpers
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def get_chunks(text):
    split = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return split.split_text(text)

def get_vector(chunks):
    return FAISS.from_texts(chunks, embeddings)

def get_rel_text(q, db):
    r = db.similarity_search(q, k=1)
    return r[0].page_content if r else "No relevant info"

def bot_response(model, query, rel_texts, history):
    ctx = " ".join(rel_texts)
    prompt = f"""
    You are IntervuAI, an experienced HR interviewer.
    Follow these rules:
    - Professional, polite, no slang.
    - Only ask/answer from the resume text.
    - If unclear, ask user to clarify.
    - Start with introductions, then projects/experience, then behavioral Qs.
    - Can summarize strengths, weaknesses, and improvements if asked.
    - Keep questions short and crisp like real interviews.

    Context from resume:
    {ctx}

    Chat history:
    {history}

    User: {query}
    IntervuAI:"""

    res = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.5))
    return res.text

model = genai.GenerativeModel("gemini-2.0-flash")

# streamlit page
st.set_page_config(page_title="IntervuAI", page_icon="💼", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = {}

with st.sidebar:
    selected = option_menu("Menu", ["Landing Page","Login/Signup","Resume Bot"],
                           icons=["house","person","chat-dots"], menu_icon="cast", default_index=0)

# landing page
if selected == "Landing Page":
    st.title("💼 IntervuAI")
    st.markdown(" Your Personal AI HR Interviewer")
    st.write(
        """
        🚀 Welcome to IntervuAI – an AI-powered interview simulator that helps you 
        practice Mock  interviews directly on your resume

        ✨ Features
        - 📄 Upload your Resume  
        - 💬 Chat with an AI HR Interviewer  
        - 🎯 Get Project & Experience-based Questions  
        - 📊 Receive Feedback on Strengths & Weaknesses  

        🎓 Why IntervuAI?
        - Prepares you for real-world interviews  
        - Gives constructive feedback based only on your resume  
        - Acts like an experienced HR professional  

        👉 Start by logging in, uploading your resume, and chat with IntervuAI to ace your interviews!
        """
    )

# login/signup
if selected == "Login/Signup":
    st.header("Login / Signup")
    if "user_id" in st.session_state:
        st.info(f"Logged in as {st.session_state['first_name']} {st.session_state['last_name']}")
        if st.button("Logout"):
            st.session_state.clear()
            st.success("Logged out")
    else:
        act = st.selectbox("Action", ["Login","Sign Up"])
        if act=="Sign Up":
            fn = st.text_input("First name")
            ln = st.text_input("Last name")
            dob = st.date_input("Date of Birth")
            em = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.button("Sign Up"):
                ok, msg = sign_up(fn, ln, dob, em, pw)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            em = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.button("Login"):
                u = login(em, pw)
                if u:
                    st.session_state["user_id"], st.session_state["first_name"], st.session_state["last_name"] = u
                    st.success(f"Welcome {u[1]} {u[2]}!")
                    st.session_state.messages[u[0]] = []
                else:
                    st.error("Invalid credentials")

# resume bot
if selected == "Resume Bot":
    st.subheader("💬 Chat with IntervuAI")
    if "user_id" not in st.session_state:
        st.warning("Login first")
    else:
        ch = st.radio("Choose", ["Upload Resume","Chat with IntervuAI"])
        if ch=="Upload Resume":
            file = st.file_uploader("Upload Resume (PDF)", type="pdf")
            if file:
                fname = file.name
                fpath = os.path.join(UPLOAD_DIR, f"{st.session_state['user_id']}_{fname}")
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                with open(fpath,"wb") as f:
                    f.write(file.getbuffer())
                if st.button("Save file"):
                    save_file(st.session_state["user_id"], fname, fpath)
                    st.success(f"{fname} saved")
            files = get_user_files(st.session_state["user_id"])
            if files:
                for fname,fpath in files:
                    st.write(fname)
                    if st.button(f"Delete {fname}", key=f"del_{fname}"):
                        delete_file(st.session_state["user_id"], fname)
                        if os.path.exists(fpath):
                            os.remove(fpath)
                        st.success(f"{fname} deleted")
        else:
            files = get_user_files(st.session_state["user_id"])
            if not files:
                st.warning("No resumes uploaded")
            else:
                s_file = st.selectbox("Select resume", [f[0] for f in files])
                if s_file:
                    path = [f[1] for f in files if f[0]==s_file][0]
                    reader = PdfReader(path)
                    text = "".join([p.extract_text() or "" for p in reader.pages])
                    db = get_vector(get_chunks(text))
                    skey = f"rag_{st.session_state['user_id']}_{s_file}"
                    if skey not in st.session_state:
                        st.session_state[skey]=[]
                    hist = st.session_state[skey]
                    for m in hist:
                        st.chat_message(m["role"]).markdown(m["content"])
                    q = st.chat_input("Ask/Answer as part of the interview...")
                    if q:
                        st.chat_message("user").markdown(q)
                        hist.append({"role":"user","content":q})
                        with st.spinner("Thinking..."):
                            rel = get_rel_text(q, db)
                            ans = bot_response(model, q, [rel], hist)
                            st.chat_message("assistant").markdown(ans)
                            hist.append({"role":"assistant","content":ans})
                        st.session_state[skey]=hist
