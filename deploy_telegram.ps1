$PROJECT_ID = gcloud config get-value project
$REGION = "europe-west1"
$SERVICE = "calistenia-telegram-bot"
$IMAGE = "gcr.io/$PROJECT_ID/$SERVICE"

# Leer variables desde .env
if (Test-Path ".env") {
    foreach ($line in (Get-Content ".env")) {
        if ($line -match "^GEMINI_API_KEY=(.*)") { $env:GEMINI_API_KEY = $Matches[1].Trim() }
        if ($line -match "^SUPABASE_URL=(.*)") { $env:SUPABASE_URL = $Matches[1].Trim() }
        if ($line -match "^SUPABASE_KEY=(.*)") { $env:SUPABASE_KEY = $Matches[1].Trim() }
        if ($line -match "^TELEGRAM_BOT_TOKEN=(.*)") { $env:TELEGRAM_BOT_TOKEN = $Matches[1].Trim() }
        if ($line -match "^TELEGRAM_ALLOWED_CHAT_ID=(.*)") { $env:TELEGRAM_ALLOWED_CHAT_ID = $Matches[1].Trim() }
        if ($line -match "^CLI_USER_EMAIL=(.*)") { $env:CLI_USER_EMAIL = $Matches[1].Trim() }
    }
}

Write-Host "[BUILD] Construyendo imagen del bot de Telegram..." -ForegroundColor Cyan
gcloud builds submit --config cloudbuild.telegram.yaml --substitutions _IMAGE=$IMAGE .

Write-Host "[RUN] Desplegando en Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE `
  --image $IMAGE `
  --region $REGION `
  --platform managed `
  --no-allow-unauthenticated `
  --min-instances 1 `
  --max-instances 1 `
  --memory 512Mi `
  --set-env-vars "GEMINI_API_KEY=$($env:GEMINI_API_KEY),SUPABASE_URL=$($env:SUPABASE_URL),SUPABASE_KEY=$($env:SUPABASE_KEY),TELEGRAM_BOT_TOKEN=$($env:TELEGRAM_BOT_TOKEN),TELEGRAM_ALLOWED_CHAT_ID=$($env:TELEGRAM_ALLOWED_CHAT_ID),CLI_USER_EMAIL=$($env:CLI_USER_EMAIL)"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Bot de Telegram desplegado." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Despliegue fallido." -ForegroundColor Red
}
