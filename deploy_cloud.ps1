# deploy_cloud.ps1 - Script de despliegue para Calistenia Coach (Windows PowerShell)

# Configuración
$PROJECT_ID = gcloud config get-value project
$SERVICE_NAME = "calistenia-coach"
$REGION = "europe-west1"

Write-Host "🚀 Iniciando despliegue de $SERVICE_NAME en el proyecto $PROJECT_ID ($REGION)..." -ForegroundColor Green

# Verificamos si la API KEY existe en el entorno
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
    $env:GEMINI_API_KEY = Read-Host "⚠️ No he encontrado tu GEMINI_API_KEY. Pégala aquí"
}

# 1. Construir la imagen en Cloud Build
Write-Host "📦 Construyendo contenedor en Cloud Build..." -ForegroundColor Cyan
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# 2. Desplegar en Cloud Run
Write-Host "🌍 Desplegando en Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --set-env-vars "GEMINI_API_KEY=$($env:GEMINI_API_KEY)"

Write-Host "✅ ¡Todo listo, Javi! Tu app está desplegada en Cloud Run." -ForegroundColor Green
