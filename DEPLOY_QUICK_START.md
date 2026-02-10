# ⚡ Quick Deployment Command Reference

## 🎯 One-Command Deployment (After Railway is ready)

### Windows (PowerShell):
```powershell
.\deploy.ps1 -RailwayUrl "https://your-railway-url.up.railway.app"
```

### Linux/Mac (Bash):
```bash
chmod +x deploy.sh
./deploy.sh https://your-railway-url.up.railway.app
```

---

## 🚂 Railway Setup (First Time)

1. **Go to Railway Dashboard:** https://railway.app/dashboard

2. **New Project from GitHub:**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select: `FixIt-AI-Multi-Agent-Visual-Troubleshooting-Orchestrator`
   - Railway auto-detects Dockerfile ✅

3. **Add Environment Variables:**
   ```
   GEMINI_API_KEY=AIzaSyBmcw4vrX9wqMwVAl7Q3r5MOAQFydn-Fok
   GEMINI_MODEL_NAME=gemini-2.5-flash-lite
   ENABLE_WEB_GROUNDING=true
   ```

4. **Generate Public Domain:**
   - Settings → Networking → "Generate Domain"
   - Copy URL (e.g., `https://fixit-backend-production.up.railway.app`)

5. **Verify Backend:**
   ```bash
   curl https://your-railway-url.up.railway.app/health
   ```

---

## 🎨 Vercel Deployment (Manual Alternative)

### Option 1: Using Deploy Script (Recommended)
See above - use `deploy.ps1` or `deploy.sh`

### Option 2: Manual Steps
```bash
cd frontend

# Update environment
echo "NEXT_PUBLIC_API_URL=https://your-railway-url.up.railway.app" > .env.production

# Deploy
vercel --prod

# Follow prompts for first-time setup
```

---

## 🔄 Update CORS After Vercel Deployment

1. **Get Vercel URL** from deployment output
2. **Add to Railway:**
   - Railway Dashboard → Your Project → Variables
   - Add: `FRONTEND_URL` = `https://your-vercel-url.vercel.app`
3. **Railway auto-redeploys** ✅

---

## ✅ Verification

### Test Backend:
```bash
curl https://your-railway-url.up.railway.app/health
```

### Test Frontend:
1. Open: `https://your-vercel-url.vercel.app`
2. Upload test image
3. Check console for errors
4. Verify API calls work

---

## 📋 Environment Variables Summary

### Railway (Backend)
- `GEMINI_API_KEY` - Your Gemini API key ⚠️ Required
- `GEMINI_MODEL_NAME` - Model to use (default: gemini-2.5-flash-lite)
- `ENABLE_WEB_GROUNDING` - Enable web search (true/false)
- `FRONTEND_URL` - Vercel frontend URL (for CORS)

### Vercel (Frontend)
- `NEXT_PUBLIC_API_URL` - Railway backend URL ⚠️ Required

---

## 🐛 Quick Troubleshooting

### CORS Error in Frontend
- ✅ Verify `FRONTEND_URL` is set in Railway
- ✅ Check it matches exact Vercel URL (including https://)
- ✅ Railway redeployed after adding variable

### 404 API Errors
- ✅ Check `NEXT_PUBLIC_API_URL` in Vercel
- ✅ Verify Railway backend is running
- ✅ Test `/health` endpoint directly

### Backend 500 Errors
- ✅ Check Railway logs
- ✅ Verify `GEMINI_API_KEY` is correct
- ✅ Check API quota on Google AI Studio

---

## 📁 Files Created

- ✅ `Dockerfile` - Railway container definition
- ✅ `.dockerignore` - Build optimization
- ✅ `vercel.json` - Vercel configuration
- ✅ `deploy.ps1` - Windows deployment script
- ✅ `deploy.sh` - Linux/Mac deployment script
- ✅ `.env.railway.template` - Railway env template
- ✅ `PRODUCTION_DEPLOYMENT.md` - Full guide
- ✅ Backend CORS updated with env variable support

---

## 🎯 Current Status

✅ All deployment files created and pushed to GitHub
✅ Railway Dockerfile ready and tested
✅ Backend CORS configured for production
✅ Vercel configuration created
✅ Deployment scripts ready

### What's Ready:
- Repository: https://github.com/SumitPatel-HQ/FixIt-AI-Multi-Agent-Visual-Troubleshooting-Orchestrator.git
- Branch: master
- Latest commit: Production deployment automation

### Next Action Required:
1. Create Railway project from dashboard (link provided above)
2. Run deployment script with Railway URL
3. Test production deployment

---

**Need help?** See [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) for detailed guide.
