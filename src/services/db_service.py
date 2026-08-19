from src.config.database import obtener_conexion
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje


def guardar_destino(destino):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        query = """
            INSERT INTO destinos (ciudad, pais) 
            VALUES (%s, %s)
            RETURNING id;
        """
        cursor.execute(query, (destino.ciudad, destino.pais))

        destino_id = cursor.fetchone()[0]
        conexion.commit()
        return destino_id

    except Exception as error:
        conexion.rollback()
        print(f"error al guardar el destino: {error}")
        return None

    finally:
        cursor.close()
        conexion.close()


def guardar_hospedaje(hospedaje):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        query = """
            INSERT INTO hospedajes (nombre, tipo, precio_noche, calificacion, direccion, url_reserva, destino_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        cursor.execute(
            query,
            (
                hospedaje.nombre, hospedaje.tipo,
                hospedaje.precio_noche, hospedaje.calificacion,
                hospedaje.direccion, hospedaje.url_reserva,
                hospedaje.destino_id)
            )

        hospedaje_id = cursor.fetchone()[0]
        conexion.commit()
        return hospedaje_id

    except Exception as error:
        conexion.rollback()
        print(f"error al guardar el hospedaje: {error}")
        return None

    finally:
        cursor.close()
        conexion.close()


def obtener_destinos():

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        query = "SELECT id, ciudad, pais FROM destinos;"
        cursor.execute(query)
        filas = cursor.fetchall()

        destinos = []
        for fila in filas:
            destino = Destino(id=fila[0], ciudad=fila[1], pais=fila[2])
            destinos.append(destino)

        return destinos
    except Exception as error:
        print(f"error al obtener los destinos: {error}")
        return []
    finally:
        cursor.close()
        conexion.close()


def obtener_hospedajes_por_destino(destino_id):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        query = """
            SELECT id, nombre, tipo, precio_noche, calificacion,
            direccion, url_reserva, destino_id FROM hospedajes
            WHERE destino_id = %s;
        """
        cursor.execute(query, (destino_id,))
        filas = cursor.fetchall()

        hospedajes = []
        for fila in filas:
            hospedaje = Hospedaje(
                id=fila[0],
                nombre=fila[1],
                tipo=fila[2],
                precio_noche=fila[3],
                calificacion=fila[4],
                direccion=fila[5],
                url_reserva=fila[6],
                destino_id=fila[7]
            )
            hospedajes.append(hospedaje)

        return hospedajes
    except Exception as error:
        print(f"error al obtener los hospedajes: {error}")
        return []
    finally:
        cursor.close()
        conexion.close()


def obtener_o_crear_destino(destino: Destino):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        ciudad = destino.ciudad
        pais = destino.pais

        if not ciudad or not pais:
            raise ValueError("ciudad y pais son obligatorios")

        ciudad = ciudad.strip().lower()
        pais = pais.strip().lower()

        if not ciudad or not pais:
            raise ValueError("ciudad y pais no pueden quedar vacios")

        query = (
            """
            SELECT id, ciudad, pais 
            FROM destinos 
            WHERE LOWER(ciudad) = %s AND LOWER(pais) = %s;
            """
        )

        cursor.execute(query, (ciudad, pais))

        resultado = cursor.fetchone()

        if resultado:
            return resultado[0]
        else:
            id_nuevo_destino = guardar_destino(Destino(ciudad=ciudad, pais=pais))
            return id_nuevo_destino

    except Exception as error:
        print(f"error al obtener o crear el destino: {error}")
        return None
    finally:
        cursor.close()
        conexion.close()


