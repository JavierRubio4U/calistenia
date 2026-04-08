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

# Exponer el puerto predeterminado de Streamlit (aunque Cloud Run usara $PORT)
ENV PORT=8080
EXPOSE 8080

# Comando para arrancar Streamlit (ajustando a la variable PORT de Cloud Run)
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0
