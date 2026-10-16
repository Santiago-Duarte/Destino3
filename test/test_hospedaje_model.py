import unittest

from src.models.hospedaje import Hospedaje


class TestHospedaje(unittest.TestCase):
    def _crear_hospedaje(self, **campos):
        valores = {
            "nombre": "Hotel de prueba",
            "tipo": "hotel",
            "precio_noche": None,
            "calificacion": None,
            "direccion": None,
            "url_reserva": None,
            "destino_id": 1,
        }
        valores.update(campos)
        return Hospedaje(**valores)

    def test_google_place_id_es_none_por_defecto(self):
        hospedaje = self._crear_hospedaje()

        self.assertIsNone(hospedaje.google_place_id)

    def test_google_place_id_conserva_un_texto(self):
        hospedaje = self._crear_hospedaje(google_place_id="ChIJ123")

        self.assertEqual(hospedaje.google_place_id, "ChIJ123")
