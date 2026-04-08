import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Configuracion real
password = "xNtvlpDehQqxawan"
project_id = "hhqgvccgadthuztwonzu"
pooler_host = "aws-0-eu-central-1.pooler.supabase.com"

# El truco: [password];[project_id]
modified_password = f"{password};{project_id}"

# Intentamos la conexion
test_url = f"postgresql://postgres:{modified_password}@{pooler_host}:6543/postgres"

print(f"Probando conexion con el truco del Project ID en el password...")
try:
    conn = psycopg2.connect(test_url, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print(f"✅ CONEXIÓN EXITOSA!")
    conn.close()
    
    # Si funciona, lo guardamos en el .env
    with open(".env", "w") as f:
        f.write(f"GEMINI_API_KEY=YOUR_GEMINI_API_KEY\n")
        f.write(f"DATABASE_URL={test_url}\n")
    print("Base de datos configurada correctamente en .env")
    
except Exception as e:
    print(f"❌ Fallo de nuevo: {e}")
