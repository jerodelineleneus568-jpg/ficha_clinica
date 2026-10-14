import tempfile
import unittest
from pathlib import Path
from app import create_app
from app.models.database import get_db
from app.models.usuario_model import crear_usuario
from app.models.clinica_model import ProfesionalModel

class ClinicaTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'CARGAR_DEMO':False,'DATABASE':str(Path(self.tmp.name)/'test.sqlite'),
            'SECRET_KEY':'a'*64,'TRUSTED_HOSTS':['localhost']})
        self.c=self.app.test_client()
        with self.app.app_context():
            ProfesionalModel.crear('Profesional A','Medicina','Médico')
            ProfesionalModel.crear('Profesional B','Enfermería','Enfermero')
            for user,rol,id in [('admin','admin',None),('recepcion','recepcion',None),('auditor','auditor',None),('clinicoa','profesional',1),('clinicob','profesional',2)]:
                crear_usuario(user,user,'Frase de prueba larga',rol,id)
    def tearDown(self):
        self.tmp.cleanup()
    def get(self,url):
        return self.c.get(url,base_url='https://localhost')
    def post(self,url,**data):
        self.get('/login')
        with self.c.session_transaction() as s:
            csrf=s['csrf']
        return self.c.post(url,base_url='https://localhost',data=dict(csrf=csrf,**data))
    def login(self,user):
        self.c=self.app.test_client()
        return self.post('/login',username=user,password='Frase de prueba larga')
    def paciente(self):
        self.login('recepcion')
        return self.post('/pacientes/nuevo',documento='FICTICIO-1',nombre='Paciente ficticio',nacimiento='2000-01-01')
    def test_roles_e_identidad_atenciones(self):
        self.paciente()
        for user in ['clinicoa','clinicob']:
            self.login(user)
            self.assertEqual(self.post('/pacientes/1/atenciones',fecha='2020-01-01',motivo='Control',diagnostico='DIAGNOSTICO_SECRETO',tratamiento='Prueba').status_code,302)
        with self.app.app_context():
            ids=[r[0] for r in get_db().execute('SELECT profesional_id FROM atenciones ORDER BY id')]
            self.assertEqual(ids,[1,2])
        self.login('clinicoa')
        self.assertIn(b'DIAGNOSTICO_SECRETO',self.get('/pacientes/1').data)
        self.assertEqual(self.post('/pacientes/1/atenciones',profesional_id='2',fecha='2020-01-01',motivo='Control',diagnostico='X',tratamiento='X').status_code,403)
        self.assertEqual(self.post('/pacientes/1/eliminar',confirmar='ELIMINAR').status_code,403)
        self.assertEqual(self.get('/usuarios').status_code,403)
        self.login('recepcion')
        self.assertNotIn(b'DIAGNOSTICO_SECRETO',self.get('/pacientes/1').data)
        self.assertEqual(self.post('/pacientes/1/atenciones',fecha='2020-01-01',motivo='X',diagnostico='X',tratamiento='X').status_code,403)
        self.login('auditor')
        self.assertEqual(self.get('/pacientes/1').status_code,403)
        self.assertEqual(self.get('/auditoria').status_code,200)
        self.login('admin')
        self.post('/pacientes/1/eliminar',confirmar='ELIMINAR')
        self.assertEqual(self.get('/pacientes/1').status_code,404)
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM atenciones').fetchone()[0],2)
    def test_csrf_sesiones_y_https(self):
        self.assertEqual(self.get('/').status_code,302)
        self.assertEqual(self.c.get('/login',base_url='http://localhost').status_code,400)
        self.assertEqual(self.c.get('/login',base_url='https://atacante.invalid').status_code,400)
        r=self.login('admin')
        cookie=r.headers.get('Set-Cookie','')
        self.assertIn('Secure',cookie)
        self.assertIn('HttpOnly',cookie)
        self.assertIn('SameSite=Lax',cookie)
        self.assertIn('frame-ancestors',r.headers['Content-Security-Policy'])
        self.assertIn('Strict-Transport-Security',r.headers)
        self.assertEqual(self.c.post('/logout',base_url='https://localhost').status_code,400)
        self.post('/logout')
        self.assertEqual(self.get('/usuarios').status_code,302)
        self.login('admin')
        with self.app.app_context():
            db=get_db();db.execute('UPDATE sesiones SET ultima=0');db.commit()
        self.assertEqual(self.get('/usuarios').status_code,302)
    def test_bloqueo_validaciones_y_xss(self):
        for _ in range(5):
            self.assertEqual(self.post('/login',username='admin',password='incorrecta').status_code,401)
        self.assertEqual(self.post('/login',username='admin',password='Frase de prueba larga').status_code,429)
        with self.app.app_context():
            db=get_db();db.execute('DELETE FROM intentos');db.commit()
        self.login('recepcion')
        self.post('/pacientes/nuevo',documento='FICTICIO',nombre='<script>alert(1)</script>',nacimiento='2000-01-01')
        self.assertNotIn(b'<script>',self.get('/').data)
        self.assertIn(b'&lt;script&gt;',self.get('/').data)
        self.post('/pacientes/nuevo',documento='FICTICIO',nombre='Duplicado',nacimiento='2000-01-01')
        self.post('/pacientes/nuevo',documento='FUTURO',nombre='X',nacimiento='2999-01-01')
        with self.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM pacientes').fetchone()[0],1)
    def test_desactivacion_revoca_sesion_y_no_borra_auditoria(self):
        self.login('clinicoa');other=self.c
        self.login('admin')
        with self.app.app_context():
            id=get_db().execute("SELECT id FROM usuarios WHERE username='clinicoa'").fetchone()[0]
        self.post(f'/usuarios/{id}/estado')
        self.assertEqual(other.get('/',base_url='https://localhost').status_code,302)
        with self.app.app_context():
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                get_db().execute('DELETE FROM auditoria')
    def test_password_revoca_todas_las_sesiones(self):
        self.login('admin');other=self.c
        self.login('admin')
        self.assertEqual(self.post('/password',anterior='Frase de prueba larga',nueva='Otra frase secreta larga').status_code,302)
        self.assertEqual(other.get('/usuarios',base_url='https://localhost').status_code,302)
        self.assertEqual(self.post('/login',username='admin',password='Otra frase secreta larga').status_code,302)
