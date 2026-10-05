class Usuario:
    def __init__(self, id: int | None, nombre: str, apellido: str, correo: str, password_hash: str) -> None:
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.correo = correo
        self.password_hash = password_hash
