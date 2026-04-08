# deploy_cloud.ps1 - Script de despliegue para Calistenia Coach (Windows PowerShell)
# Uso: .\deploy_cloud.ps1
# Requiere: gcloud CLI instalado y autenticado

# Configuracion
$PROJECT_ID = gcloud config get-value project
$SERVICE_NAME = "calistenia-coach"
$REGION = "europe-west1"
$IMAGE = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "Iniciando despliegue de $SERVICE_NAME en $PROJECT_ID ($REGION)..." -ForegroundColor Green

# ── 1. Verificar que gcloud esta autenticado ───────────────────
$account = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>&1
if (-not $account) {
    Write-Host "ERROR: No hay cuenta activa en gcloud. Ejecuta: gcloud auth login" -ForegroundColor Red
    exit 1
}
Write-Host "Cuenta activa: $account" -ForegroundColor Dim

# ── 2. Obtener GEMINI_API_KEY ──────────────────────────────────
if (-not $env:GEMINI_API_KEY) {
    if (Test-Path ".env") {
        $env_content = Get-Content ".env"
        foreach ($line in $env_content) {
            if ($line -match "^GEMINI_API_KEY=(.*)") {
                $env:GEMINI_API_KEY = $Matches[1].Trim()
                break
            }
        }
    }
}

if (-not $env:GEMINI_API_KEY) {
    $env:GEMINI_API_KEY = Read-Host "No se encontro GEMINI_API_KEY. Pegala aqui"
}

if (-not $env:GEMINI_API_KEY) {
    Write-Host "ERROR: GEMINI_API_KEY es obligatoria." -ForegroundColor Red
    exit 1
}

# ── 3. Build de la imagen en Cloud Build ──────────────────────
Write-Host "Construyendo imagen en Cloud Build..." -ForegroundColor Cyan
gcloud builds submit --tag $IMAGE

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: El build fallo (codigo $LASTEXITCODE). Revisa los logs anteriores." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Build completado." -ForegroundColor Green

# ── 4. Desplegar en Cloud Run ─────────────────────────────────
Write-Host "Desplegando en Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --set-env-vars "GEMINI_API_KEY=$($env:GEMINI_API_KEY)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: El despliegue fallo (codigo $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

# ── 5. Mostrar URL final ───────────────────────────────────────
$url = gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"
Write-Host ""
Write-Host "Despliegue completado!" -ForegroundColor Green
Write-Host "URL: $url" -ForegroundColor Yellow
