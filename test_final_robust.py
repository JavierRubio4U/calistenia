import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Credenciales de Javi
password = "xNtvlpDehQqxawan"
project_id = "hhqgvccgadthuztwonzu"
pooler_host = "aws-0-eu-central-1.pooler.supabase.com"

# El formato oficial de Supabase para el Pooler IPv4
# user: postgres.[project-id]
# host: [region].pooler.supabase.com
# port: 6543 (Transaction) o 5432 (Session)
# SSL: Obligatorio

test_configs = [
    f"postgresql://postgres.{project_id}:{password}@{pooler_host}:6543/postgres?sslmode=require",
    f"postgresql://postgres.{project_id}:{password}@{pooler_host}:5432/postgres?sslmode=require",
    f"postgresql://postgres:{password}@{project_id}.supabase.co:5432/postgres?sslmode=require"
]

print("🚀 Iniciando suite de pruebas de conexion final...")

for url in test_configs:
    print(f"Probando: {url.split('@')[-1]}")
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        print("✅ ¡EXITO! Esta es la configuracion correcta.")
        conn.close()
        
        # Guardar en .env
        with open(".env", "w") as f:
            f.write("GEMINI_API_KEY=YOUR_GEMINI_API_KEY\n")
            f.write(f"DATABASE_URL={url}\n")
        break
    except Exception as e:
        print(f"❌ Fallo: {e}")

print("Pruebas terminadas.")
