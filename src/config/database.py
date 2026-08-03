import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def obtener_conexion():
    try:
        conexion = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )

        return conexion

    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")

obtener_conexion()