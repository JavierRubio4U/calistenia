import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Configuracion real
password = "xNtvlpDehQqxawan"
project_id = "hhqgvccgadthuztwonzu"
pooler_host = "aws-0-eu-central-1.pooler.supabase.com"

# Esta es la forma mas robusta de pasar el Tenant ID en el Pooler de Supabase
# usando el parametro options de PostgreSQL.
try:
    print(f"Probando conexion con parametro 'options'...")
    # El parametro options permite decirle al pooler exactamente que proyecto queremos
    conn = psycopg2.connect(
        host=pooler_host,
        port=6543,
        user="postgres",
        password=password,
        database="postgres",
        options=f"-c project={project_id}",
        connect_timeout=10,
        sslmode="require"
    )
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("✅ ¡CONEXIÓN ESTABLECIDA CON ÉXITO!")
    conn.close()
except Exception as e:
    print(f"❌ Fallo con options: {e}")
