 💼 IntervuAI – AI Resume Interview Bot

IntervuAI is your Personal AI HR interviewer.  
Upload your resume and chat with an **AI-powered HR bot** that asks realistic interview questions based only on your resume.



 🚀 Features
- 📄 Upload Resume (PDF)
- 💬 Chat with IntervuAI (HR-style questions)
- 🎯 Resume-grounded responses (no hallucination)
- 📊 Feedback on Strengths, Weaknesses, and Skills
- 🔑 Secure Login/Signup with SQLite



 🛠️ Tech Stack
- Frontend: Streamlit
- Database: SQLite
- Embeddings: Google Generative AI
- LLM: Gemini (Gemini-2.0-Flash)
- Vector DB: FAISS



📂 Project Structure
IntervuAI/
│── README.md
│── requirements.txt
│── main.py
│── .env
│── resume_bot.db
│
└── user_uploaded_files/

⚙️ Setup

1. Clone the repo:
   git clone https://github.com/soujanya-006/IntervuAI
   cd IntervuAI

2. Install dependencies:
pip install -r requirements.txt

3.Add your Google API key in .env:
GOOGLE_API_KEY= 

4.Run the app:
streamlit run main.py