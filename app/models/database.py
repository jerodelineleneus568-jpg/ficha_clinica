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

        if 'activo' not in {r['name'] for r in db.execute('PRAGMA table_info(pacientes)')}:
            db.execute('ALTER TABLE pacientes ADD COLUMN activo INTEGER NOT NULL DEFAULT 1')
        db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL, password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('admin','recepcion','profesional','auditor')),
            profesional_id INTEGER REFERENCES profesionales(id),
            activo INTEGER NOT NULL DEFAULT 1,
            CHECK(rol != 'profesional' OR profesional_id IS NOT NULL));
        CREATE UNIQUE INDEX IF NOT EXISTS usuario_profesional_unico ON usuarios(profesional_id) WHERE profesional_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS sesiones (
            token_hash TEXT PRIMARY KEY,usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            creada INTEGER NOT NULL,ultima INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS intentos (
            clave TEXT PRIMARY KEY, fallos INTEGER NOT NULL, desde INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY,usuario_id INTEGER REFERENCES usuarios(id),
            accion TEXT NOT NULL,entidad TEXT NOT NULL,referencia INTEGER,fecha INTEGER NOT NULL);
        CREATE TRIGGER IF NOT EXISTS auditoria_no_update BEFORE UPDATE ON auditoria
            BEGIN SELECT RAISE(ABORT,'Auditoría inmutable'); END;
        CREATE TRIGGER IF NOT EXISTS auditoria_no_delete BEFORE DELETE ON auditoria
            BEGIN SELECT RAISE(ABORT,'Auditoría inmutable'); END;
        """)
        db.commit()

        if 'activo' not in {r['name'] for r in db.execute('PRAGMA table_info(profesionales)')}:
            db.execute('ALTER TABLE profesionales ADD COLUMN activo INTEGER NOT NULL DEFAULT 1')
        db.commit()
        if 'paciente_id' not in {r['name'] for r in db.execute('PRAGMA table_info(usuarios)')}:
            db.execute('PRAGMA foreign_keys=OFF')
            try:
                with db:
                    db.execute("""CREATE TABLE usuarios_nuevos (
                        id INTEGER PRIMARY KEY,username TEXT NOT NULL UNIQUE,nombre TEXT NOT NULL,password_hash TEXT NOT NULL,
                        rol TEXT NOT NULL CHECK(rol IN ('admin','recepcion','profesional','auditor','paciente')),
                        profesional_id INTEGER REFERENCES profesionales(id),paciente_id INTEGER REFERENCES pacientes(id),
                        activo INTEGER NOT NULL DEFAULT 1,
                        CHECK((rol='profesional' AND profesional_id IS NOT NULL AND paciente_id IS NULL)
                           OR (rol='paciente' AND paciente_id IS NOT NULL AND profesional_id IS NULL)
                           OR (rol IN ('admin','recepcion','auditor') AND profesional_id IS NULL AND paciente_id IS NULL)))""")
                    db.execute("""INSERT INTO usuarios_nuevos(id,username,nombre,password_hash,rol,profesional_id,activo)
                        SELECT id,username,nombre,password_hash,rol,CASE WHEN rol='profesional' THEN profesional_id ELSE NULL END,activo FROM usuarios""")
                    db.execute('DROP TABLE usuarios')
                    db.execute('ALTER TABLE usuarios_nuevos RENAME TO usuarios')
                    db.execute('CREATE UNIQUE INDEX usuario_profesional_unico ON usuarios(profesional_id) WHERE profesional_id IS NOT NULL')
            finally:
                db.execute('PRAGMA foreign_keys=ON')
        db.executescript("""
        CREATE UNIQUE INDEX IF NOT EXISTS usuario_paciente_unico ON usuarios(paciente_id) WHERE paciente_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS admisiones (
            id INTEGER PRIMARY KEY,paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
            profesional_id INTEGER REFERENCES profesionales(id),fecha TEXT NOT NULL,
            especialidad TEXT NOT NULL,motivo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente','en_atencion','atendido','cancelado')),
            activo INTEGER NOT NULL DEFAULT 1,creado_por INTEGER NOT NULL REFERENCES usuarios(id),
            creada INTEGER NOT NULL,version INTEGER NOT NULL DEFAULT 1);
        CREATE UNIQUE INDEX IF NOT EXISTS admision_abierta_unica ON admisiones(paciente_id)
            WHERE activo=1 AND estado IN ('pendiente','en_atencion');
        """)
        if 'admision_id' not in {r['name'] for r in db.execute('PRAGMA table_info(atenciones)')}:
            db.execute('ALTER TABLE atenciones ADD COLUMN admision_id INTEGER REFERENCES admisiones(id)')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS atencion_admision_unica ON atenciones(admision_id) WHERE admision_id IS NOT NULL')
        db.commit()
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('La migración detectó una referencia inválida. Conserva el respaldo y revisa la base.')

        db.executescript("""
        CREATE TABLE IF NOT EXISTS tipos_atencion (
            id INTEGER PRIMARY KEY,nombre TEXT NOT NULL UNIQUE,minutos INTEGER NOT NULL CHECK(minutos BETWEEN 5 AND 240),
            cupos INTEGER NOT NULL DEFAULT 1 CHECK(cupos BETWEEN 1 AND 20),activo INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS agenda_bloques (
            id INTEGER PRIMARY KEY,profesional_id INTEGER NOT NULL REFERENCES profesionales(id),
            tipo_id INTEGER NOT NULL REFERENCES tipos_atencion(id),fecha TEXT NOT NULL,inicio TEXT NOT NULL,fin TEXT NOT NULL,
            cupos INTEGER NOT NULL CHECK(cupos BETWEEN 1 AND 20),activo INTEGER NOT NULL DEFAULT 1,
            creado_por INTEGER NOT NULL REFERENCES usuarios(id),version INTEGER NOT NULL DEFAULT 1);
        CREATE INDEX IF NOT EXISTS agenda_busqueda ON agenda_bloques(profesional_id,fecha,activo);
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY,paciente_id INTEGER NOT NULL REFERENCES pacientes(id),nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,mime TEXT NOT NULL,tamano INTEGER NOT NULL,sha256 TEXT NOT NULL,
            contenido BLOB NOT NULL,creado_por INTEGER NOT NULL REFERENCES usuarios(id),creada INTEGER NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1);
        """)
        if 'slot_id' not in {r['name'] for r in db.execute('PRAGMA table_info(admisiones)')}:
            with db:
                db.execute('ALTER TABLE admisiones ADD COLUMN slot_id INTEGER REFERENCES agenda_bloques(id)')
                db.execute('DROP INDEX IF EXISTS admision_abierta_unica')
                db.execute("""CREATE UNIQUE INDEX admision_abierta_unica ON admisiones(paciente_id)
                    WHERE activo=1 AND estado IN ('pendiente','en_atencion') AND slot_id IS NULL""")
        db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS cita_paciente_bloque ON admisiones(paciente_id,slot_id)
            WHERE activo=1 AND estado != 'cancelado' AND slot_id IS NOT NULL""")
        if not db.execute("SELECT 1 FROM configuracion WHERE clave='tipos_agenda_v1'").fetchone():
            with db:
                for nombre,minutos in [('Consulta general',60),('Control',30),('Primera consulta',60),('Evaluación',45)]:
                    db.execute('INSERT OR IGNORE INTO tipos_atencion(nombre,minutos,cupos) VALUES(?,?,1)',(nombre,minutos))
                db.execute("INSERT INTO configuracion(clave,valor) VALUES('tipos_agenda_v1','1')")
        db.commit()
