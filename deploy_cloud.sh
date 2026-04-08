#!/bin/bash
# deploy_cloud.sh - Scripts de despliegue para Calistenia Coach (Google Cloud Run)

PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="calistenia-coach"
REGION="europe-west1"

echo "🚀 Iniciando despliegue de $SERVICE_NAME en el proyecto $PROJECT_ID ($REGION)..."

# 1. Construir la imagen en Cloud Build (sin subirla desde local)
echo "📦 Construyendo contenedor en Cloud Build..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 2. Desplegar en Cloud Run (permitiendo acceso público sin autenticación)
echo "🌍 Desplegando en Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY"

echo "✅ ¡Todo listo! Tu app debería estar disponible en la URL generada por Cloud Run."
