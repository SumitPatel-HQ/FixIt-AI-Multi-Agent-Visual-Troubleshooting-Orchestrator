# 🚀 Production Deployment Guide - FixIt AI

## ✅ Completed Steps

### Backend Preparation
- ✅ Created production Dockerfile with Python 3.11-slim
- ✅ Created .dockerignore to optimize build
- ✅ Fixed CMD format for Railway (exec form with shell)
- ✅ Committed and pushed to GitHub: `https://github.com/SumitPatel-HQ/FixIt-AI-Multi-Agent-Visual-Troubleshooting-Orchestrator.git`

---

## 🔧 Railway Backend Deployment Steps

### Step 1: Create Railway Project
1. Go to **[Railway Dashboard](https://railway.app/dashboard)**
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select: `SumitPatel-HQ/FixIt-AI-Multi-Agent-Visual-Troubleshooting-Orchestrator`
4. Railway will auto-detect the Dockerfile

### Step 2: Configure Environment Variables
In Railway project settings → **Variables** tab, add:

```bash
GEMINI_API_KEY=AIzaSyBmcw4vrX9wqMwVAl7Q3r5MOAQFydn-Fok
GEMINI_MODEL_NAME=gemini-2.5-flash-lite
ENABLE_WEB_GROUNDING=true
```

### Step 3: Enable Public Domain
1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Copy the generated URL (format: `https://your-app.up.railway.app`)

### Step 4: Verify Backend
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "0.3.0",
  "pipeline": "enhanced-gate-based-routing"
}
```

---

## 🎨 Frontend Deployment to Vercel

### Step 1: Install Vercel CLI (if not installed)
```bash
npm install -g vercel
```

### Step 2: Deploy Frontend
```bash
cd frontend
vercel
```

Follow prompts:
- **Set up and deploy?** `Yes`
- **Which scope?** Select your account
- **Link to existing project?** `No`
- **Project name:** `fixit-ai-frontend` (or your choice)
- **Directory:** Leave as `.` (we're already in frontend folder)
- **Override settings?** `No`

### Step 3: Set Environment Variable in Vercel
After deployment, add the Railway backend URL:

```bash
# Replace with your actual Railway URL
vercel env add NEXT_PUBLIC_API_URL production
# When prompted, enter: https://your-app.up.railway.app
```

Or via Vercel Dashboard:
1. Go to project → **Settings** → **Environment Variables**
2. Add: `NEXT_PUBLIC_API_URL` = `https://your-app.up.railway.app`

### Step 4: Redeploy Frontend
```bash
vercel --prod
```

---

## 🔗 Update CORS in Backend

After getting the Vercel URL (format: `https://fixit-ai-frontend.vercel.app`), update backend CORS:

1. Edit `backend/main.py` line 56-62
2. Replace:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

With:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fixit-ai-frontend.vercel.app",  # Your Vercel URL
        "http://localhost:3000",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. Commit and push - Railway will auto-redeploy:
```bash
git add backend/main.py
git commit -m "Update CORS for production frontend"
git push origin master
```

---

## ✅ Verification Checklist

### Backend Health Check
```bash
curl https://your-backend.up.railway.app/health
```

### Frontend Access
- Open: `https://your-frontend.vercel.app`
- Check browser console for errors
- Verify API calls go to Railway URL

### End-to-End Test
1. Upload a device image
2. Enter troubleshooting query
3. Verify:
   - ✅ No CORS errors in console
   - ✅ API response received
   - ✅ Results displayed correctly
   - ✅ Follow-up questions work

---

## 🔑 Quick Reference

### Your Deployment URLs
```bash
# Backend (Railway)
BACKEND_URL=https://[your-railway-subdomain].up.railway.app

# Frontend (Vercel)
FRONTEND_URL=https://[your-project-name].vercel.app
```

### Environment Variables Summary
**Railway (Backend):**
- `GEMINI_API_KEY`
- `GEMINI_MODEL_NAME`
- `ENABLE_WEB_GROUNDING`

**Vercel (Frontend):**
- `NEXT_PUBLIC_API_URL` (Railway backend URL)

---

## 🐛 Troubleshooting

### Railway Build Fails
- Check logs in Railway dashboard
- Verify Dockerfile syntax
- Ensure requirements.txt is complete

### Frontend Can't Connect to Backend
- Verify CORS allows Vercel domain
- Check `NEXT_PUBLIC_API_URL` in Vercel env vars
- Inspect browser console network tab

### 500 Errors from Backend
- Check Railway logs for Python errors
- Verify `GEMINI_API_KEY` is set correctly
- Check Gemini API quota

---

## 📝 Next Steps

1. **Get Railway URL** from dashboard after deployment
2. **Deploy frontend** to Vercel
3. **Update CORS** in backend with Vercel URL
4. **Test production** deployment end-to-end
5. **Monitor** Railway logs for any issues

---

**Status:** ✅ All files prepared and pushed to GitHub
**Repository:** https://github.com/SumitPatel-HQ/FixIt-AI-Multi-Agent-Visual-Troubleshooting-Orchestrator.git
