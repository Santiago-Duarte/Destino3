import unittest

from src.config.database import obtener_conexion
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.models.busqueda import Busqueda
from src.models.recomendacion import Recomendacion
from src.repositories.destino_repository import DestinoRepository
from src.repositories.hospedaje_repository import HospedajeRepository
from src.repositories.busqueda_repository import BusquedaRepository
from src.repositories.recomendacion_repository import RecomendacionRepository

TABLAS = "busquedas, recomendaciones, evaluaciones_ia, hospedajes, destinos, usuarios"


class BaseDBTestCase(unittest.TestCase):
    """Base de las pruebas que necesitan base de datos de pruebas.

    Vacía las tablas antes y después de cada prueba y se salta toda la clase
    si no hay conexión, para que la suite nunca dependa de una BD real.
    """

    @classmethod
    def setUpClass(cls):
        cls.conexion = obtener_conexion()
        if cls.conexion is None:
            raise unittest.SkipTest("No se pudo conectar a la base de datos de testing")
        cls.cursor = cls.conexion.cursor()
        cls._insertar_usuario_semilla()
        cls.destino_repo = DestinoRepository()
        cls.hospedaje_repo = HospedajeRepository()

    @classmethod
    def tearDownClass(cls):
        cls._clean_db()
        cls.cursor.close()
        cls.conexion.close()

    def setUp(self):
        self._clean_db()
        self._insertar_usuario_semilla()

    def tearDown(self):
        self._clean_db()

    @classmethod
    def _clean_db(cls):
        with cls.conexion.cursor() as cursor:
            cursor.execute(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE")
        cls.conexion.commit()

    @classmethod
    def _insertar_usuario_semilla(cls):
        cls.cursor.execute(
            "INSERT INTO usuarios (nombre, apellido, correo, password_hash) "
            "VALUES ('admin', 'admin', 'admin@admin.com', 'admin') "
            "ON CONFLICT (correo) DO UPDATE SET nombre = 'admin' "
            "RETURNING id"
        )
        cls.usuario_seed_id = cls.cursor.fetchone()[0]
        cls.conexion.commit()

    def crear_destino(self, ciudad="Medellin", pais="Colombia"):
        return self.destino_repo.guardar(Destino(ciudad=ciudad, pais=pais))

    def crear_hospedaje(self, destino_id, **campos):
        valores = dict(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=destino_id,
            google_place_id=None,
        )
        valores.update(campos)
        return self.hospedaje_repo.guardar_lote([Hospedaje(**valores)])[0]

    def crear_busqueda_con_recomendaciones(self, destino_id, num_hospedajes=3):
        hospedajes = []
        for i in range(1, num_hospedajes + 1):
            h = self.crear_hospedaje(destino_id, nombre=f"Hotel {i}")
            hospedajes.append(h)

        busqueda_repo = BusquedaRepository()
        recomendacion_repo = RecomendacionRepository()

        busqueda = Busqueda(
            id=None,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda_id = busqueda_repo.guardar(busqueda)

        recomendaciones = [
            Recomendacion(id=None, busqueda_id=busqueda_id, hospedaje_id=h, posicion=posicion)
            for posicion, h in enumerate(hospedajes, start=1)
        ]

        recomendacion_repo.guardar_lote(recomendaciones)

        return busqueda_id, recomendaciones
