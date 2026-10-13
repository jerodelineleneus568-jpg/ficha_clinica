from .database import get_db

class PacienteModel:
    @staticmethod
    def listar(busqueda=''):
        return get_db().execute('SELECT * FROM pacientes WHERE nombre LIKE ? OR documento LIKE ? ORDER BY nombre',
                                ('%'+busqueda+'%', '%'+busqueda+'%')).fetchall()
    @staticmethod
    def obtener(id):
        return get_db().execute('SELECT * FROM pacientes WHERE id=?', (id,)).fetchone()
    @staticmethod
    def crear(datos):
        db = get_db()
        with db:
            c = db.execute('INSERT INTO pacientes(documento,nombre,nacimiento,telefono,correo) VALUES(?,?,?,?,?)', datos)
        return c.lastrowid
    @staticmethod
    def eliminar(id):
        db = get_db()
        with db:
            db.execute('DELETE FROM pacientes WHERE id=?', (id,))

class ProfesionalModel:
    @staticmethod
    def listar():
        return get_db().execute('SELECT * FROM profesionales ORDER BY nombre').fetchall()
    @staticmethod
    def obtener(id):
        return get_db().execute('SELECT * FROM profesionales WHERE id=?', (id,)).fetchone()
    @staticmethod
    def crear(nombre, especialidad, cargo):
        db = get_db()
        with db:
            db.execute('INSERT INTO profesionales(nombre,especialidad,cargo) VALUES(?,?,?)', (nombre,especialidad,cargo))

class AtencionModel:
    @staticmethod
    def listar(paciente_id):
        return get_db().execute("""SELECT a.*, p.nombre AS profesional, p.especialidad, p.cargo
            FROM atenciones a JOIN profesionales p ON p.id=a.profesional_id
            WHERE a.paciente_id=? ORDER BY a.fecha DESC, a.id DESC""", (paciente_id,)).fetchall()
    @staticmethod
    def crear(datos):
        db = get_db()
        with db:
            db.execute('INSERT INTO atenciones(paciente_id,profesional_id,fecha,motivo,diagnostico,tratamiento) VALUES(?,?,?,?,?,?)', datos)
