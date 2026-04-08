import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
url = os.getenv("DATABASE_URL")

# Forzamos la IP si el host falla
# pooler_ip = "18.198.145.223" 
# La URL en el .env ya deberia estar actualizada por mi paso anterior, 
# pero voy a probar con la IP directamente aqui para asegurar.

try:
    print(f"Intentando conectar a: {url.split('@')[-1]}...")
    conn = psycopg2.connect(url, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"✅ CONEXIÓN EXITOSA: {cur.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"❌ FALLO DE CONEXIÓN: {e}")
