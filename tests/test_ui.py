import unittest
import test_clinica

class InterfazTest(unittest.TestCase):
    def setUp(self):
        self.base=test_clinica.ClinicaTest();self.base.setUp()
    def tearDown(self):
        self.base.tearDown()
    def test_inicio_y_navegacion_segun_rol(self):
        b=self.base
        for rol in ['admin','recepcion','clinicoa','auditor']:
            self.assertEqual(b.login(rol).headers['Location'],'/inicio')
            r=b.get('/inicio')
            self.assertEqual(r.status_code,200)
            self.assertIn(b'aria-current="page"',r.data)
            if rol=='auditor':
                self.assertNotIn(b'Pacientes y fichas',r.data)
                self.assertIn(b'Abrir auditor',r.data)
            if rol=='clinicoa':self.assertIn(b'Profesional A',r.data)
        with b.get('/static/app.js') as asset:
            self.assertEqual(asset.status_code,200)
        self.assertIn("script-src 'self'",r.headers['Content-Security-Policy'])
        self.assertNotIn('unsafe-inline',r.headers['Content-Security-Policy'])
    def test_formularios_renderizan_con_ayudas(self):
        b=self.base;b.paciente();b.login('admin')
        for path,marker in [('/agenda/generar',b'data-agenda-preview'),('/admisiones/nueva',b'data-new-patient'),('/usuarios',b'data-role-help')]:
            r=b.get(path)
            self.assertEqual(r.status_code,200,path)
            self.assertIn(marker,r.data)
        r=b.post('/agenda/generar',profesional_id='1',tipo_id='1',desde='incorrecta',hasta='incorrecta',inicio='08:00',fin='09:00',minutos='60',cupos='1',dias='0')
        self.assertIn(b'role="alert"',r.data)
    def test_inicio_paciente_y_profesional_no_muestran_otros(self):
        from app.models.database import get_db
        from app.models.usuario_model import crear_usuario
        from app.services.agenda_service import hoy
        b=self.base;b.paciente()
        b.post('/pacientes/nuevo',documento='OTRO',nombre='PACIENTE AJENO',nacimiento='2000-01-01')
        for pid,prof in [('1','1'),('2','2')]:
            b.post('/admisiones/nueva',paciente_id=pid,fecha=hoy(),especialidad='Medicina' if prof=='1' else 'Enfermería',motivo='Control',profesional_id=prof)
        with b.app.app_context():
            crear_usuario('pacienteui','Cuenta paciente','Frase de prueba larga','paciente',paciente_id=1)
        b.login('pacienteui');r=b.get('/inicio')
        self.assertEqual(r.status_code,200)
        self.assertIn(b'Mis citas por atender',r.data)
        self.assertNotIn(b'PACIENTE AJENO',r.data)
        b.login('clinicoa');r=b.get('/inicio')
        self.assertIn(b'Paciente ficticio',r.data)
        self.assertNotIn(b'PACIENTE AJENO',r.data)
