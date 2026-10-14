from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from io import BytesIO
import unittest
import test_clinica
from app.models.database import get_db
from app.models.clinica_model import PacienteModel
from app.models.usuario_model import crear_usuario
from app.services.agenda_service import reservar,ConflictoAgenda,hoy

class AgendaDocumentosTest(unittest.TestCase):
    def setUp(self):
        self.b=test_clinica.ClinicaTest();self.b.setUp()
        self.fecha=hoy()
        with self.b.app.app_context():
            self.tipo=get_db().execute("SELECT id FROM tipos_atencion WHERE nombre='Consulta general'").fetchone()[0]
            self.pid=PacienteModel.crear(('PAC-1','Paciente Agenda','2000-01-01','',''))
            self.pid2=PacienteModel.crear(('PAC-2','Otro Paciente','2000-01-01','',''))
        self.b.login('recepcion')
    def tearDown(self):self.b.tearDown()
    def generar(self,prof='1',minutos='60',cupos='1',inicio='08:00',fin='10:00',**otros):
        return self.b.post('/agenda/generar',profesional_id=prof,tipo_id=str(self.tipo),desde=self.fecha,hasta=self.fecha,inicio=inicio,fin=fin,minutos=minutos,cupos=cupos,dias=[str(date.fromisoformat(self.fecha).weekday())],**otros)
    def test_generacion_rendimiento_pausas_y_cruce_rechazado(self):
        self.assertEqual(self.generar(minutos='30',fin='11:00',pausa_inicio='09:00',pausa_fin='10:00').status_code,302)
        with self.b.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM agenda_bloques').fetchone()[0],4)
        self.assertEqual(self.generar().status_code,200)
        with self.b.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM agenda_bloques').fetchone()[0],4)
        r=self.b.get('/agenda?desde='+self.fecha+'&hasta='+self.fecha)
        self.assertEqual(r.status_code,200);self.assertIn(b'2.0 pacientes/hora',r.data)
        self.assertEqual(self.b.get('/agenda/bloques/1').status_code,200)
        self.assertEqual(self.b.get('/agenda/bloques/1/reservar').status_code,200)
    def test_reserva_capacidad_reprogramacion_y_cancelacion(self):
        self.generar()
        self.assertEqual(self.b.post('/agenda/bloques/1/reservar',paciente_id=str(self.pid),motivo='Prueba').status_code,302)
        self.assertEqual(self.b.post('/agenda/bloques/1/reservar',paciente_id=str(self.pid2),motivo='Sin cupo').status_code,200)
        self.assertEqual(self.b.get('/agenda/citas/1/reprogramar').status_code,200)
        self.assertEqual(self.b.post('/agenda/citas/1/reprogramar',slot_id='2',version='1').status_code,302)
        with self.b.app.app_context():
            self.assertEqual(get_db().execute('SELECT slot_id FROM admisiones WHERE id=1').fetchone()[0],2)
        self.assertEqual(self.b.post('/agenda/citas/1/cancelar',version='2',confirmar='CANCELAR').status_code,302)
        self.assertEqual(self.b.post('/agenda/bloques/2/reservar',paciente_id=str(self.pid2),motivo='Cupo liberado').status_code,302)
    def test_profesional_ve_solo_su_agenda_e_historial(self):
        self.generar();self.generar(prof='2')
        self.b.post('/agenda/bloques/1/reservar',paciente_id=str(self.pid),motivo='Cita')
        self.b.login('clinicob')
        self.assertEqual(self.b.get('/agenda/bloques/1').status_code,404)
        self.b.login('clinicoa')
        self.assertEqual(self.b.get('/agenda/bloques/1').status_code,200)
        self.assertEqual(self.b.post('/agenda/generar').status_code,403)
        self.b.post('/admisiones/1/atender',version='1',accion='iniciar')
        self.b.post('/admisiones/1/atender',version='2',accion='finalizar',motivo='Consulta',diagnostico='Evaluación ficticia',tratamiento='Indicaciones ficticias')
        with self.b.app.app_context():
            self.assertEqual(get_db().execute('SELECT admision_id FROM atenciones').fetchone()[0],1)
        self.assertIn(b'Evaluaci',self.b.get('/pacientes/1').data)
    def test_cruce_paciente_entre_profesionales_y_cupos_grupales(self):
        self.generar(cupos='2');self.generar(prof='2')
        self.assertEqual(self.b.post('/agenda/bloques/1/reservar',paciente_id='1',motivo='Una').status_code,302)
        self.assertEqual(self.b.post('/agenda/bloques/1/reservar',paciente_id='2',motivo='Dos').status_code,302)
        self.assertEqual(self.b.post('/agenda/bloques/3/reservar',paciente_id='1',motivo='Cruce').status_code,200)
        with self.b.app.app_context():self.assertEqual(get_db().execute('SELECT COUNT(*) FROM admisiones').fetchone()[0],2)
    def test_concurrencia_no_sobrevende_cupos(self):
        self.generar()
        def intento(pid):
            with self.b.app.app_context():
                try:
                    reservar(1,pid,'Prueba concurrente',2)
                    return 'ok'
                except ConflictoAgenda:
                    return 'sin cupo'
        with ThreadPoolExecutor(max_workers=2) as pool:
            r=list(pool.map(intento,[self.pid,self.pid2]))
        self.assertEqual(sorted(r),['ok','sin cupo'])
        with self.b.app.app_context():self.assertEqual(get_db().execute('SELECT COUNT(*) FROM admisiones').fetchone()[0],1)
    def test_crud_bloque_tipos_y_vincular_admision(self):
        self.generar()
        self.assertEqual(self.b.get('/agenda/bloques/1/editar').status_code,200)
        self.assertEqual(self.b.post('/agenda/bloques/1/editar',version='1',inicio='08:00',fin='08:30',cupos='1').status_code,302)
        self.b.post('/admisiones/nueva',paciente_id='1',fecha=self.fecha,especialidad='Medicina',motivo='Ya en lista',profesional_id='1')
        self.assertEqual(self.b.post('/agenda/bloques/1/reservar',paciente_id='1',admision_id='1',motivo='Agendada').status_code,302)
        self.assertEqual(self.b.post('/agenda/bloques/1/eliminar',confirmar='ELIMINAR').status_code,200)
        self.assertEqual(self.b.post('/agenda/bloques/2/eliminar',confirmar='ELIMINAR').status_code,302)
        self.b.login('admin')
        self.assertEqual(self.b.get('/agenda/tipos').status_code,200)
        self.assertEqual(self.b.post('/agenda/tipos',nombre='Tipo prueba',minutos='20',cupos='1').status_code,302)
        self.assertEqual(self.b.get('/agenda/tipos/1/editar').status_code,200)
    def test_documentos_carga_permisos_y_no_mime_falseado(self):
        pdf=b'%PDF-1.4\nDocumento ficticio de prueba\n%%EOF'
        self.assertEqual(self.b.post('/pacientes/1/documentos',descripcion='Examen ficticio',archivo=(BytesIO(pdf),'examen.pdf')).status_code,302)
        self.assertEqual(self.b.get('/documentos/1/descargar').status_code,403)
        self.assertEqual(self.b.post('/pacientes/1/documentos',descripcion='Falso',archivo=(BytesIO(b'HTML falso'),'falso.pdf')).status_code,200)
        self.b.login('clinicoa')
        r=self.b.get('/documentos/1/descargar')
        self.assertEqual(r.status_code,200);self.assertEqual(r.data,pdf);self.assertIn('attachment',r.headers['Content-Disposition'])
        with self.b.app.app_context():
            crear_usuario('paciente1','Paciente','Frase de prueba larga','paciente',paciente_id=1)
            crear_usuario('paciente2','Paciente2','Frase de prueba larga','paciente',paciente_id=2)
        self.b.login('paciente2');self.assertEqual(self.b.get('/documentos/1/descargar').status_code,404)
        self.assertEqual(self.b.get('/pacientes/1/documentos').status_code,404)
        self.b.login('paciente1');self.assertEqual(self.b.get('/documentos/1/descargar').status_code,200)
        self.b.login('admin')
        self.assertEqual(self.b.get('/documentos/1/editar').status_code,200)
        self.assertEqual(self.b.post('/documentos/1/editar',descripcion='Descripción nueva').status_code,302)
        self.assertEqual(self.b.post('/documentos/1/eliminar',confirmar='ELIMINAR').status_code,302)
        self.assertEqual(self.b.get('/documentos/1/descargar').status_code,404)
    def test_cuota_documentos_y_portal_hora(self):
        self.b.app.config['DOC_PATIENT_QUOTA']=10
        pdf=b'%PDF-1.4\nPrueba\n%%EOF'
        self.assertEqual(self.b.post('/pacientes/1/documentos',descripcion='Sobre cuota',archivo=(BytesIO(pdf),'a.pdf')).status_code,200)
        with self.b.app.app_context():
            self.assertEqual(get_db().execute('SELECT COUNT(*) FROM documentos').fetchone()[0],0)
        self.generar();self.b.post('/agenda/bloques/1/reservar',paciente_id='1',motivo='Cita')
        with self.b.app.app_context():crear_usuario('paciente1','Paciente','Frase de prueba larga','paciente',paciente_id=1)
        self.b.login('paciente1')
        self.assertIn(b'08:00',self.b.get('/mis-admisiones').data)
        self.assertEqual(self.b.get('/agenda').status_code,403)
