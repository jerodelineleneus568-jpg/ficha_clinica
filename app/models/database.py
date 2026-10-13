import sqlite3
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

def init_db(app):
    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()
    with app.app_context():
        get_db().executescript("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY, documento TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL, nacimiento TEXT NOT NULL,
            telefono TEXT NOT NULL DEFAULT '', correo TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS profesionales (
            id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, especialidad TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS atenciones (
            id INTEGER PRIMARY KEY,
            paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
            profesional_id INTEGER NOT NULL REFERENCES profesionales(id),
            fecha TEXT NOT NULL, motivo TEXT NOT NULL,
            diagnostico TEXT NOT NULL, tratamiento TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_atenciones_paciente ON atenciones(paciente_id);
        """)

        db = get_db()
        columnas = {r['name'] for r in db.execute('PRAGMA table_info(profesionales)')}
        if 'cargo' not in columnas:
            db.execute("ALTER TABLE profesionales ADD COLUMN cargo TEXT NOT NULL DEFAULT 'Profesional de salud'")
        db.execute('CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)')
        if app.config.get('CARGAR_DEMO', True):
            with db:
                if not db.execute("SELECT 1 FROM configuracion WHERE clave='profesionales_demo_v1'").fetchone():
                    ejemplos = [
                        ('Ana Pérez (demo)', 'Medicina general', 'Médica'),
                        ('Luis Soto (demo)', 'Enfermería', 'Enfermero'),
                        ('Camila Rojas (demo)', 'Psicología', 'Psicóloga'),
                        ('Diego Muñoz (demo)', 'Kinesiología', 'Kinesiólogo'),
                        ('Valentina Díaz (demo)', 'Nutrición', 'Nutricionista'),
                        ('Carolina Torres (demo)', 'Obstetricia', 'Matrona')]
                    for nombre, especialidad, cargo in ejemplos:
                        if not db.execute('SELECT 1 FROM profesionales WHERE nombre=? AND especialidad=?', (nombre, especialidad)).fetchone():
                            db.execute('INSERT INTO profesionales(nombre,especialidad,cargo) VALUES(?,?,?)', (nombre,especialidad,cargo))
                    db.execute("INSERT INTO configuracion(clave,valor) VALUES('profesionales_demo_v1','1')")
        db.commit()
