import sqlite3
import tempfile
import unittest
from pathlib import Path
from app import create_app
from app.models.database import get_db

class ActualizacionTest(unittest.TestCase):
    def test_migracion_preserva_datos_y_demo_no_se_duplica(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath = str(Path(tmp)/'vieja.sqlite')
            db = sqlite3.connect(dbpath)
            db.executescript("""
                CREATE TABLE pacientes(id INTEGER PRIMARY KEY,documento TEXT NOT NULL UNIQUE,nombre TEXT NOT NULL,nacimiento TEXT NOT NULL,telefono TEXT NOT NULL DEFAULT '',correo TEXT NOT NULL DEFAULT '');
                CREATE TABLE profesionales(id INTEGER PRIMARY KEY,nombre TEXT NOT NULL,especialidad TEXT NOT NULL);
                CREATE TABLE atenciones(id INTEGER PRIMARY KEY,paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,profesional_id INTEGER NOT NULL REFERENCES profesionales(id),fecha TEXT NOT NULL,motivo TEXT NOT NULL,diagnostico TEXT NOT NULL,tratamiento TEXT NOT NULL);
                INSERT INTO pacientes VALUES(1,'FICTICIO','Paciente anterior','2000-01-01','','');
                INSERT INTO profesionales VALUES(1,'Profesional anterior','Medicina');
                INSERT INTO atenciones VALUES(1,1,1,'2020-01-01','Control','Prueba','Prueba');
            """)
            db.commit(); db.close()
            for _ in range(2):
                app = create_app({'TESTING':True,'DATABASE':dbpath,'SECRET_KEY':'test'})
                client=app.test_client()
                self.assertEqual(client.get('/').status_code,200)
                r=client.get('/pacientes/1')
                self.assertEqual(r.status_code,200)
                self.assertIn(b'Paciente anterior',r.data)
                self.assertIn(b'Profesional anterior',r.data)
                self.assertIn(b'Registrar atenci',r.data)
                self.assertEqual(client.get('/profesionales').status_code,200)
                with app.app_context():
                    self.assertEqual(get_db().execute('SELECT COUNT(*) FROM profesionales').fetchone()[0],7)
                    self.assertEqual(get_db().execute('SELECT COUNT(*) FROM atenciones').fetchone()[0],1)
