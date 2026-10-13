import tempfile
import unittest
from pathlib import Path
from app import create_app
from app.models.database import get_db

class ClinicaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING':True, 'CARGAR_DEMO':False, 'SECRET_KEY':'test', 'DATABASE':str(Path(self.tmp.name)/'test.sqlite')})
        self.client = self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as s:
            self.csrf = s['csrf']
    def tearDown(self):
        self.tmp.cleanup()
    def post(self,url,**datos):
        return self.client.post(url,data=dict(csrf=self.csrf,**datos),follow_redirects=True)
    def paciente(self):
        return self.post('/pacientes/nuevo',documento='TEST-1',nombre='Paciente ficticio',nacimiento='2000-01-01')
    def test_historial_distintos_profesionales_y_eliminacion(self):
        self.post('/profesionales',nombre='Profesional A',especialidad='Medicina',cargo='Médico')
        self.post('/profesionales',nombre='Profesional B',especialidad='Enfermería',cargo='Enfermero')
        self.assertEqual(self.paciente().status_code,200)
        for id in (1,2):
            r=self.post('/pacientes/1/atenciones',profesional_id=str(id),fecha='2020-01-01',motivo='Control',diagnostico='Evaluación ficticia',tratamiento='Indicaciones ficticias')
            self.assertEqual(r.status_code,200)
        r=self.client.get('/pacientes/1')
        self.assertIn(b'Profesional A',r.data)
        self.assertIn(b'Profesional B',r.data)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM atenciones').fetchone()[0],2)
        self.post('/pacientes/1/eliminar',confirmar='incorrecto')
        self.assertEqual(self.client.get('/pacientes/1').status_code,200)
        self.post('/pacientes/1/eliminar',confirmar='ELIMINAR')
        self.assertEqual(self.client.get('/pacientes/1').status_code,404)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM atenciones').fetchone()[0],0)
    def test_validaciones_y_csrf(self):
        self.paciente()
        self.paciente()
        self.post('/pacientes/nuevo',documento='TEST-2',nombre='Futuro',nacimiento='2999-01-01')
        self.post('/pacientes/1/atenciones',profesional_id='999',fecha='2020-01-01',motivo='X',diagnostico='X',tratamiento='X')
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM pacientes').fetchone()[0],1)
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM atenciones').fetchone()[0],0)
        self.assertEqual(self.client.post('/pacientes/1/eliminar',data={'confirmar':'ELIMINAR'}).status_code,400)
        self.assertEqual(self.client.get('/pacientes/999').status_code,404)

if __name__ == '__main__':
    unittest.main()
