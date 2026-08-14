import unittest
from unittest.mock import patch

from src.services.ai_evaluator import *


class TestAIEvaluator(unittest.TestCase):

    def test_seleccionar_candidatos_con_lista_vacia(self):
        hospedajes = []
        presupuesto_max = 100
        resultado = seleccionar_candidatos(hospedajes, presupuesto_max)
        self.assertEqual(resultado, [])