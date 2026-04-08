import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

# Configuracion detectada
password = "xNtvlpDehQqxawan"
project_id = "hhqgvccgadthuztwonzu"
pooler_host = "aws-0-eu-central-1.pooler.supabase.com"

# Variantes de usuario para el pooler de Supabase
user_variants = [
    f"postgres.{project_id}",
    f"{project_id}.postgres",
    "postgres"
]

for user in user_variants:
    # Construimos la URL de test para el pooler (Port 6543)
    test_url = f"postgresql://{user}:{password}@{pooler_host}:6543/postgres"
    
    print(f"Probando usuario: {user}...")
    try:
        conn = psycopg2.connect(test_url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        print(f"✅ CONEXIÓN EXITOSA con usuario: {user}")
        conn.close()
        # Si funciona, actualizamos el .env con esta version ganadora
        with open(".env", "a") as f:
            f.write(f"\n# Conexion verificada funcionando\nDATABASE_URL={test_url}\n")
        break
    except Exception as e:
        print(f"❌ Fallo con {user}: {e}")

print("Test finalizado.")
