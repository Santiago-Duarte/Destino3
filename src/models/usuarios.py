class Usuario:
    def __init__(self, id, nombre, apellido, correo, password_hash):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.correo = correo
        self.password_hash = password_hash
