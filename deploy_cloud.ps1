# deploy_cloud.ps1 - Script de despliegue para Calistenia Coach (Supabase Version Final)

# Configuracion
$PROJECT_ID = gcloud config get-value project
$SERVICE_NAME = "calistenia-coach"
$REGION = "europe-west1"
$IMAGE = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "[DEPLOY] Iniciando despliegue de $SERVICE_NAME (Modo HTTPS Robusto) en $PROJECT_ID ($REGION)..." -ForegroundColor Green

# ── 1. Obtener Variables de Entorno ────────────────────────────
if (Test-Path ".env") {
    $env_content = Get-Content ".env"
    foreach ($line in $env_content) {
        if ($line -match "^GEMINI_API_KEY=(.*)") { $env:GEMINI_API_KEY = $Matches[1].Trim() }
        if ($line -match "^SUPABASE_URL=(.*)") { $env:SUPABASE_URL = $Matches[1].Trim() }
        if ($line -match "^SUPABASE_KEY=(.*)") { $env:SUPABASE_KEY = $Matches[1].Trim() }
    }
}

if (-not $env:GEMINI_API_KEY) { $env:GEMINI_API_KEY = Read-Host "No se encontro GEMINI_API_KEY" }
if (-not $env:SUPABASE_URL) { $env:SUPABASE_URL = Read-Host "No se encontro SUPABASE_URL" }
if (-not $env:SUPABASE_KEY) { $env:SUPABASE_KEY = Read-Host "No se encontro SUPABASE_KEY" }

# ── 2. Build de la imagen en Cloud Build ──────────────────────
Write-Host "[BUILD] Construyendo imagen en Cloud Build..." -ForegroundColor Cyan
gcloud builds submit --tag $IMAGE --quiet

# ── 3. Desplegar en Cloud Run ─────────────────────────────────
Write-Host "[RUN] Desplegando en Cloud Run..." -ForegroundColor Cyan

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --set-env-vars "GEMINI_API_KEY=$($env:GEMINI_API_KEY),SUPABASE_URL=$($env:SUPABASE_URL),SUPABASE_KEY=$($env:SUPABASE_KEY)" `
    --timeout=600

if ($LASTEXITCODE -eq 0) {
    $url = gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"
    Write-Host "[SUCCESS] Despliegue completado con exito!" -ForegroundColor Green
    Write-Host "[URL] URL del servicio: $url" -ForegroundColor Yellow
} else {
    Write-Host "[ERROR] El despliegue ha fallado." -ForegroundColor Red
}
