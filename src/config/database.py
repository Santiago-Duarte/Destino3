import os
import psycopg2


def obtener_conexion():
    entorno = os.getenv('ENVIRONMENT', 'development')

    if entorno == 'testing':
        base_de_datos = 'DB_TEST_NAME'
    else:
        base_de_datos = 'DB_NAME'

    try:
        conexion = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv(base_de_datos),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )

        return conexion

    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None