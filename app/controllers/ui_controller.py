from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint,g,render_template
from ..models.database import get_db
from ..models.admision_model import AdmisionModel
from ..models.agenda_model import AgendaModel
from ..security import roles_required,ROLES

bp=Blueprint('ui',__name__)

@bp.get('/inicio')
@roles_required(*ROLES)
def inicio():
    rol=g.usuario['rol'];db=get_db();hoy=datetime.now(ZoneInfo('America/Santiago')).date().isoformat()
    if rol=='auditor':
        cantidad=db.execute('SELECT COUNT(*) FROM auditoria').fetchone()[0]
        return render_template('inicio.html',estadisticas=[('Eventos registrados',cantidad)],admisiones=[],agenda=[],hoy=hoy)
    if rol=='paciente':
        citas=AdmisionModel.listar(paciente_id=g.usuario['paciente_id'])
        futuras=[c for c in citas if c['fecha']>=hoy and c['estado'] in ('pendiente','en_atencion')]
        documentos=db.execute('SELECT COUNT(*) FROM documentos WHERE paciente_id=? AND activo=1',(g.usuario['paciente_id'],)).fetchone()[0]
        return render_template('inicio.html',estadisticas=[('Mis citas por atender',len(futuras)),('Mis documentos',documentos)],admisiones=futuras[:5],agenda=[],hoy=hoy)
    prof=g.usuario['profesional_id'] if rol=='profesional' else None
    citas=[a for a in AdmisionModel.listar(profesional_id=prof) if a['fecha']==hoy]
    agenda=AgendaModel.listar(hoy,hoy,profesional_id=prof)
    stats=[('Pendientes hoy',sum(a['estado']=='pendiente' for a in citas)),('En atención hoy',sum(a['estado']=='en_atencion' for a in citas)),('Atendidos hoy',sum(a['estado']=='atendido' for a in citas)),('Cupos libres hoy',sum(max(0,b['cupos']-b['ocupados']) for b in agenda))]
    return render_template('inicio.html',estadisticas=stats,admisiones=citas[:6],agenda=agenda[:5],hoy=hoy)
