# Dockerfile - Calistenia Coach (Google Cloud Run Edition)

FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para sounddevice (aunque en el servidor no grabaremos audio, la lib podría fallar si falta)
RUN apt-get update && apt-get install -y \
    libasound2 \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Forzar salida sin buffer para que print() aparezca en Cloud Run logs
ENV PYTHONUNBUFFERED=1

# Exponer el puerto predeterminado de Streamlit (aunque Cloud Run usara $PORT)
ENV PORT=8080
EXPOSE 8080

# Script de arranque: genera secrets.toml desde variables de entorno y lanza Streamlit
COPY docker_entrypoint.sh /app/docker_entrypoint.sh
RUN chmod +x /app/docker_entrypoint.sh

CMD ["/app/docker_entrypoint.sh"]
