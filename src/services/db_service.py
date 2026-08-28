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

    if hospedaje.destino_id is None:
        print("error al guardar el hospedaje: destino_id es obligatorio")
        return None

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
        ciudad = (destino.ciudad or "").strip().lower()
        pais = (destino.pais or "").strip().lower()

        if not ciudad or not pais:
            raise ValueError("ciudad y pais son obligatorios y no pueden quedar vacios")

        cursor.execute(
            "SELECT id FROM destinos WHERE LOWER(TRIM(ciudad)) = %s AND LOWER(TRIM(pais)) = %s;",
            (ciudad, pais),
        )
        resultado = cursor.fetchone()
        if resultado:
            return resultado[0]

        cursor.execute(
            "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id;",
            (ciudad, pais),
        )
        insertado = cursor.fetchone()
        if insertado:
            conexion.commit()
            return insertado[0]

        # Conflicto por carrera: otro proceso insertó el mismo destino
        cursor.execute(
            "SELECT id FROM destinos WHERE LOWER(TRIM(ciudad)) = %s AND LOWER(TRIM(pais)) = %s;",
            (ciudad, pais),
        )
        existente = cursor.fetchone()
        if existente:
            conexion.commit()
            return existente[0]

        conexion.commit()
        return None

    except Exception as error:
        try:
            conexion.rollback()
        except Exception:
            pass
        print(f"error al obtener o crear el destino: {error}")
        return None
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conexion.close()
        except Exception:
            pass


