import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Configuracion real
password = "xNtvlpDehQqxawan"
project_id = "hhqgvccgadthuztwonzu"
pooler_host = "aws-0-eu-central-1.pooler.supabase.com"

# Probamos con el Project ID como nombre de la base de datos
test_url = f"postgresql://postgres:{password}@{pooler_host}:6543/{project_id}"

print(f"Probando conexion con Project ID como DB Name...")
try:
    conn = psycopg2.connect(test_url, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print(f"✅ CONEXIÓN EXITOSA!")
    conn.close()
except Exception as e:
    print(f"❌ Fallo: {e}")

# Probamos con el Project ID as username (sin punto)
test_url_2 = f"postgresql://{project_id}:{password}@{pooler_host}:6543/postgres"
print(f"Probando conexion con Project ID como Username...")
try:
    conn = psycopg2.connect(test_url_2, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print(f"✅ CONEXIÓN EXITOSA!")
    conn.close()
except Exception as e:
    print(f"❌ Fallo: {e}")
