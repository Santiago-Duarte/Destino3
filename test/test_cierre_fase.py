import unittest
from pathlib import Path


SRC = Path(__file__).parents[1] / "src"

NOMBRES_PROHIBIDOS = ("SERPAPI_KEY", "GEMINI_API_KEY")


class TestCierreFase(unittest.TestCase):

    def archivos_python(self):
        return SRC.rglob("*.py")

    def test_no_hay_print_en_src(self):
        for archivo in self.archivos_python():
            with self.subTest(archivo=archivo):
                self.assertNotIn("print(", archivo.read_text(encoding="utf-8"))

    def test_los_logs_no_mencionan_nombres_de_credenciales(self):
        for archivo in self.archivos_python():
            contenido = archivo.read_text(encoding="utf-8")
            lineas_log = [
                linea for linea in contenido.splitlines()
                if "logger." in linea
            ]
            for linea in lineas_log:
                with self.subTest(archivo=archivo, linea=linea):
                    self.assertFalse(any(nombre in linea for nombre in NOMBRES_PROHIBIDOS))

    def test_los_logs_no_usan_logger_exception(self):
        """logger.exception() imprime el traceback completo, que puede
        exponer credenciales embebidas en URLs de error."""
        for archivo in self.archivos_python():
            contenido = archivo.read_text(encoding="utf-8")
            for linea in contenido.splitlines():
                with self.subTest(archivo=archivo, linea=linea):
                    self.assertNotIn("logger.exception", linea)

    def test_los_logs_no_exponen_str_de_excepciones(self):
        """Loguear str(error) o %s con error puede incluir la URL de la
        petición con la API key embebida."""
        patrones_peligrosos = (
            '"%s", error',
            '"%s", e)',
            '"%s", e ',
            "%s', error",
            "%s', e)",
        )
        for archivo in self.archivos_python():
            contenido = archivo.read_text(encoding="utf-8")
            lineas_log = [
                linea for linea in contenido.splitlines()
                if "logger." in linea
            ]
            for linea in lineas_log:
                with self.subTest(archivo=archivo, linea=linea):
                    for patron in patrones_peligrosos:
                        self.assertNotIn(patron, linea)

    def test_las_excepciones_personalizadas_no_incluyen_str_error(self):
        """SerpApiError y similares no deben recibir str(error) como detalle
        porque eso puede incluir la URL con credenciales."""
        for archivo in self.archivos_python():
            contenido = archivo.read_text(encoding="utf-8")
            for linea in contenido.splitlines():
                if "SerpApiError(" in linea or "PersistenciaError(" in linea:
                    with self.subTest(archivo=archivo, linea=linea):
                        self.assertNotIn("str(error)", linea)
                        self.assertNotIn("str(e)", linea)

    def test_los_mensajes_de_excepcion_no_mencionan_credenciales(self):
        """raise ValueError, raise SerpApiError, etc. no deben incluir
        nombres de variables de credenciales en sus mensajes."""
        for archivo in self.archivos_python():
            contenido = archivo.read_text(encoding="utf-8")
            lineas_raise = [
                linea for linea in contenido.splitlines()
                if "raise " in linea
            ]
            for linea in lineas_raise:
                with self.subTest(archivo=archivo, linea=linea):
                    self.assertFalse(any(nombre in linea for nombre in NOMBRES_PROHIBIDOS))


if __name__ == "__main__":
    unittest.main()
