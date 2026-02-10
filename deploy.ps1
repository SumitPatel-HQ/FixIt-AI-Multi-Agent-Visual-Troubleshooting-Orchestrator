# PowerShell Deployment Script for FixIt AI
# ===========================================

param(
    [Parameter(Mandatory=$true)]
    [string]$RailwayUrl
)

Write-Host "🚀 FixIt AI Deployment Automation" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Backend URL: $RailwayUrl" -ForegroundColor Green
Write-Host ""

# Step 1: Update frontend environment
Write-Host "📝 Step 1: Updating frontend environment..." -ForegroundColor Yellow
Set-Location -Path frontend
"NEXT_PUBLIC_API_URL=$RailwayUrl" | Out-File -FilePath .env.production -Encoding utf8
Write-Host "✅ Frontend .env.production updated" -ForegroundColor Green
Write-Host ""

# Step 2: Check Vercel CLI
Write-Host "🔍 Step 2: Checking Vercel CLI..." -ForegroundColor Yellow
$vercelExists = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelExists) {
    Write-Host "📦 Installing Vercel CLI..." -ForegroundColor Yellow
    npm install -g vercel
    Write-Host "✅ Vercel CLI installed" -ForegroundColor Green
} else {
    Write-Host "✅ Vercel CLI already installed" -ForegroundColor Green
}
Write-Host ""

# Step 3: Deploy to Vercel
Write-Host "🚀 Step 3: Deploying frontend to Vercel..." -ForegroundColor Yellow
Write-Host "   (Follow the prompts if this is first deployment)" -ForegroundColor Gray
vercel --prod
Write-Host "✅ Frontend deployed to Vercel" -ForegroundColor Green
Write-Host ""

# Step 4: Instructions
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔗 Your Backend URL: $RailwayUrl" -ForegroundColor White
Write-Host "🔗 Frontend URL: Check Vercel output above" -ForegroundColor White
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Copy your Vercel URL from above" -ForegroundColor White
Write-Host "  2. Go to Railway Dashboard → Variables" -ForegroundColor White
Write-Host "  3. Add: FRONTEND_URL=<your-vercel-url>" -ForegroundColor White
Write-Host "  4. Test deployment at your Vercel URL" -ForegroundColor White
Write-Host ""
Write-Host "✅ Verify health: $RailwayUrl/health" -ForegroundColor Green
Write-Host ""

Set-Location -Path ..
