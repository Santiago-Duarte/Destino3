from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.services.db_service import guardar_destino, guardar_hospedaje

ciudad="Cartagena"
pais="Colombia"

destino = Destino(ciudad, pais)

destino_id = guardar_destino(destino)

nombre = "Hotel 1"
tipo = "hotel"
precio_noche = 100
calificacion = 4
direccion = "Calle 1"
url_reserva = "https://www.hotel1.com"

hospedaje = Hospedaje(nombre, tipo, precio_noche, calificacion, direccion, url_reserva, destino_id)

hospedaje_id = guardar_hospedaje(hospedaje)

print(f"Destino guardado con ID: {destino_id}")
print(f"Hospedaje guardado con ID: {hospedaje_id}")
