from datetime import datetime
from zoneinfo import ZoneInfo
from .models.database import get_db
from flask import g,request

ROLE_LABELS={'admin':'Administración','recepcion':'Recepción','profesional':'Profesional','paciente':'Paciente','auditor':'Auditoría'}

def register_ui(app):
    @app.context_processor
    def ui_context():
        ep=request.endpoint or ''
        seccion='Inicio'
        if ep.startswith('agenda.'):
            seccion='Tipos de atención' if 'tipo' in ep else 'Agenda'
        elif ep.startswith('admision.'):
            seccion='Mis citas' if getattr(g,'usuario',None) and g.usuario['rol']=='paciente' else 'Admisión'
        elif ep.startswith('documento.'):seccion='Documentos externos'
        elif ep.startswith('clinica.'):
            seccion='Funcionarios' if 'profesional' in ep else 'Pacientes'
        elif ep in ('auth.usuarios','auth.editar_usuario','auth.estado_usuario'):seccion='Usuarios y permisos'
        elif ep=='auth.auditoria':seccion='Auditoría'
        elif ep=='auth.password':seccion='Mi contraseña'
        elif ep=='auth.login':seccion='Iniciar sesión'
        profesional=None
        if getattr(g,'usuario',None) and g.usuario['rol']=='profesional':
            profesional=get_db().execute('SELECT nombre,cargo FROM profesionales WHERE id=?',(g.usuario['profesional_id'],)).fetchone()
        return dict(ui_seccion=seccion,ui_fecha=datetime.now(ZoneInfo('America/Santiago')).strftime('%d/%m/%Y'),
                    ui_hoy=datetime.now(ZoneInfo('America/Santiago')).date().isoformat(),ui_roles=ROLE_LABELS,ui_profesional=profesional)
