#!/bin/bash
# Deployment Automation Script for FixIt AI
# ==========================================

set -e  # Exit on error

echo "🚀 FixIt AI Deployment Automation"
echo "=================================="
echo ""

# Check if Railway URL is provided
if [ -z "$1" ]; then
    echo "❌ Error: Railway backend URL required"
    echo "Usage: ./deploy.sh <railway-backend-url>"
    echo "Example: ./deploy.sh https://fixit-backend.up.railway.app"
    exit 1
fi

RAILWAY_URL=$1
echo "✅ Backend URL: $RAILWAY_URL"
echo ""

# Step 1: Update frontend environment
echo "📝 Step 1: Updating frontend environment..."
cd frontend
echo "NEXT_PUBLIC_API_URL=$RAILWAY_URL" > .env.production
echo "✅ Frontend .env.production updated"
echo ""

# Step 2: Install Vercel CLI if not present
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
    echo "✅ Vercel CLI installed"
else
    echo "✅ Vercel CLI already installed"
fi
echo ""

# Step 3: Deploy to Vercel
echo "🚀 Step 3: Deploying frontend to Vercel..."
vercel --prod --yes
echo "✅ Frontend deployed to Vercel"
echo ""

# Step 4: Get Vercel URL
echo "📋 Getting Vercel deployment URL..."
VERCEL_URL=$(vercel inspect --wait | grep -oP 'https://[^[:space:]]+' | head -1)

if [ -z "$VERCEL_URL" ]; then
    echo "⚠️  Could not auto-detect Vercel URL"
    echo "Please check your Vercel dashboard for the deployment URL"
else
    echo "✅ Frontend URL: $VERCEL_URL"
    echo ""
    
    # Step 5: Instructions for Railway env update
    echo "📝 Step 5: Update Railway environment variable"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Go to Railway Dashboard → Your Project → Variables"
    echo "Add/Update: FRONTEND_URL=$VERCEL_URL"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Your URLs:"
echo "  Backend:  $RAILWAY_URL"
echo "  Frontend: $VERCEL_URL"
echo ""
echo "📋 Next Steps:"
echo "  1. Add FRONTEND_URL to Railway environment variables"
echo "  2. Test the deployment at: $VERCEL_URL"
echo "  3. Verify health endpoint: $RAILWAY_URL/health"
echo ""
