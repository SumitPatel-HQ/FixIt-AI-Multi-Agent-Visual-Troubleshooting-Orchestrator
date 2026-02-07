# 🚀 Quick Start Guide

Follow these steps to get **FixIt AI** up and running.

## 1. Prerequisites
Ensure you have your environment variables set up in a `.env` file:
```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash-exp
```

## 2. Start the Backend (FastAPI)
Open a terminal and run:
```powershell
.\.venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```
*The backend will be available at [http://localhost:8000](http://localhost:8000)*

## 3. Start the Frontend (Streamlit)
Open a **new** terminal and run:
```powershell
.\.venv\Scripts\activate
streamlit run streamlit_app.py
```
*The UI will open automatically at [http://localhost:8501](http://localhost:8501)*

---

## 🧪 Testing the New Pipeline
The backend now includes a **Gate-Based Routing** system. You can test it with:
- **Game Screenshots:** Should be rejected automatically.
- **Blurry Device Photos:** Should ask for clarification.
- **Valid Device Photos:** Should provide full troubleshooting steps.
