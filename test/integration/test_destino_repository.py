import unittest
import uuid
from unittest.mock import MagicMock, patch

from src.models.destino import Destino
from src.repositories.destino_repository import DestinoRepository
from test.caso_prueba_bd import BaseDBTestCase


class TestDestinoRepository(BaseDBTestCase):
    def _datos_destino(self, ciudad="Medellin", pais="Colombia"):
        return f"{ciudad}_{uuid.uuid4().hex}", pais

    def _ids_destinos(self):
        return {destino.id for destino in self.destino_repo.obtener_todos()}

    def _destinos_creados(self, ids):
        ids = set(ids)
        return [destino for destino in self.destino_repo.obtener_todos() if destino.id in ids]

    def test_guardar_y_obtener_destino(self):
        ciudad, pais = self._datos_destino()
        destino_id = self.crear_destino(ciudad=ciudad, pais=pais)

        destinos = self._destinos_creados([destino_id])

        self.assertEqual(len(destinos), 1)
        destino = destinos[0]
        self.assertEqual(destino.id, destino_id)
        self.assertEqual(destino.ciudad, ciudad)
        self.assertEqual(destino.pais, pais)

    def test_guardar_y_obtener_coordenadas(self):
        ciudad, pais = self._datos_destino()
        destino_id = self.crear_destino(
            ciudad=ciudad,
            pais=pais,
            latitud=6.2442,
            longitud=-75.5812,
        )

        destino = self._destinos_creados([destino_id])[0]

        self.assertEqual(destino.coordenadas(), (6.2442, -75.5812))

    def test_obtener_por_ciudad_pais(self):
        ciudad, pais = self._datos_destino("Medellin", "Colombia")
        destino_id = self.crear_destino(
            ciudad=ciudad,
            pais=pais,
            latitud=6.2442,
            longitud=-75.5812,
        )

        destino = self.destino_repo.obtener_por_ciudad_pais(ciudad, pais)

        self.assertIsNotNone(destino)
        self.assertEqual(destino.id, destino_id)
        self.assertEqual(destino.coordenadas(), (6.2442, -75.5812))

    def test_obtener_por_ciudad_pais_inexistente_devuelve_none(self):
        self.assertIsNone(
            self.destino_repo.obtener_por_ciudad_pais("NoExiste", "Nada")
        )

    def test_obtener_por_ciudad_pais_vacia_devuelve_none(self):
        self.assertIsNone(self.destino_repo.obtener_por_ciudad_pais("", "Colombia"))
        self.assertIsNone(self.destino_repo.obtener_por_ciudad_pais("Medellin", ""))

    def test_actualizar_coordenadas(self):
        ciudad, pais = self._datos_destino()
        destino_id = self.crear_destino(ciudad=ciudad, pais=pais)

        self.destino_repo.actualizar_coordenadas(destino_id, 6.2442, -75.5812)

        destino = self._destinos_creados([destino_id])[0]
        self.assertEqual(destino.coordenadas(), (6.2442, -75.5812))

    def test_obtener_o_crear_completa_coordenadas_faltantes(self):
        ciudad, pais = self._datos_destino()
        destino_id = self.crear_destino(ciudad=ciudad, pais=pais)

        self.destino_repo.obtener_o_crear(Destino(
            ciudad=ciudad,
            pais=pais,
            latitud=6.2442,
            longitud=-75.5812,
        ))

        destino = self._destinos_creados([destino_id])[0]
        self.assertEqual(destino.coordenadas(), (6.2442, -75.5812))

    def test_obtener_destinos_sin_registros(self):
        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_obtener_destinos_con_varios_registros(self):
        datos = [
            self._datos_destino("Medellin", "Colombia"),
            self._datos_destino("Bogota", "Colombia"),
            self._datos_destino("Buenos Aires", "Argentina"),
        ]
        ids = [self.crear_destino(ciudad=ciudad, pais=pais) for ciudad, pais in datos]

        destinos = self._destinos_creados(ids)

        self.assertEqual(len(destinos), 3)
        self.assertEqual({d.ciudad for d in destinos}, {ciudad for ciudad, _ in datos})

    def test_guardar_destino_con_caracteres_especiales(self):
        ciudad, pais = self._datos_destino("Ciudad de México", "México")
        destino_id = self.crear_destino(ciudad=ciudad, pais=pais)

        destinos = self._destinos_creados([destino_id])

        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, ciudad)
        self.assertEqual(destinos[0].pais, pais)

    def test_guardar_destino_invalido_lanza_value_error_y_no_guarda(self):
        ids_antes = self._ids_destinos()

        with self.assertRaises(ValueError):
            self.destino_repo.guardar(Destino(ciudad=None, pais="Colombia"))

        self.assertEqual(self._ids_destinos(), ids_antes)

    def test_crear_destino_cuando_no_existe(self):
        ciudad, pais = self._datos_destino("medellin", "colombia")
        nuevo_destino = Destino(ciudad=ciudad, pais=pais)

        resultado = self.destino_repo.obtener_o_crear(nuevo_destino)
        destinos = self._destinos_creados([resultado])

        self.assertIsInstance(resultado, int)
        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, ciudad)
        self.assertEqual(destinos[0].pais, pais)

    def test_llamar_dos_veces_la_misma_ciudad_devuelve_el_mismo_id(self):
        ciudad, pais = self._datos_destino()
        nuevo_destino = Destino(ciudad=ciudad, pais=pais)

        resultado1 = self.destino_repo.obtener_o_crear(nuevo_destino)
        resultado2 = self.destino_repo.obtener_o_crear(nuevo_destino)

        self.assertEqual(len(self._destinos_creados([resultado1])), 1)
        self.assertEqual(resultado1, resultado2)

    def test_obtener_o_crear_con_ciudad_invalida_lanza_value_error(self):
        ids_antes = self._ids_destinos()

        with self.assertRaises(ValueError):
            self.destino_repo.obtener_o_crear(Destino(ciudad=None, pais="Colombia"))
        with self.assertRaises(ValueError):
            self.destino_repo.obtener_o_crear(Destino(ciudad="", pais="Colombia"))

        self.assertEqual(self._ids_destinos(), ids_antes)

    def test_obtener_o_crear_con_solo_espacios_lanza_value_error(self):
        ids_antes = self._ids_destinos()

        with self.assertRaises(ValueError):
            self.destino_repo.obtener_o_crear(Destino(ciudad="   ", pais="Colombia"))

        self.assertEqual(self._ids_destinos(), ids_antes)

    def test_obtener_o_crear_conserva_el_formato_de_ciudad_y_pais(self):
        ciudad, pais = self._datos_destino("MEdellin", "CoLombia")
        nuevo_destino = Destino(f" {ciudad}  ", f" {pais}  ")

        destino_id = self.destino_repo.obtener_o_crear(nuevo_destino)

        resultado = self._destinos_creados([destino_id])

        self.assertEqual(resultado[0].ciudad, ciudad)
        self.assertEqual(resultado[0].pais, pais)


class TestObtenerOCrearDestinoCarrera(unittest.TestCase):
    """Otra transacción inserta el destino entre el SELECT inicial y el INSERT."""

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_devuelve_el_id_que_inserto_la_otra_transaccion(self, obtener_conexion):
        conexion = MagicMock()
        cursor = MagicMock()
        obtener_conexion.return_value = conexion
        conexion.cursor.return_value = cursor
        cursor.fetchone.side_effect = [None, None, (99,)]

        repo = DestinoRepository()
        resultado = repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        self.assertEqual(resultado, 99)


