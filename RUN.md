# 🚀 Quick Start Guide

Follow these steps to get **FixIt AI** up and running.


## 1. Setup Virtual Environment
Open a terminal and run the following commands to create and activate a virtual environment:
```powershell
cd backend

python -m venv .venv

.\.venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```



*The backend will be available at [http://localhost:8000](http://localhost:8000)*

## 2. Start the Frontend
Open a **new** terminal and run:
```powershell
cd frontend

pnpm install

pnpm dev
```
*The UI will open automatically at [http://localhost:3000](http://localhost:3000)*

---