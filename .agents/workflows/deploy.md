---
description: Despliegue automático de Calistenia Coach a Google Cloud Run
---

# // turbo-all

Este workflow realiza el despliegue completo sin pedir confirmaciones manuales constantes.

1. Construir la imagen en Google Cloud Build
   ```powershell
   gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/calistenia-coach --quiet
   ```

2. Desplegar en Cloud Run (HTTPS Mode)
   ```powershell
   ./deploy_cloud.ps1
   ```

3. Verificar Salud del Servicio
   ```powershell
   gcloud run services describe calistenia-coach --region europe-west1 --format="value(status.url)"
   ```
