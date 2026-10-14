from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
import re
from ..models.database import get_db
from ..models.agenda_model import AgendaModel
from .admision_service import fecha_iso,texto,evento

class ConflictoAgenda(ValueError):
    pass

def hoy():
    return datetime.now(ZoneInfo('America/Santiago')).date().isoformat()

def entero(v,nombre,minimo,maximo):
    try:
        n=int(v)
    except (ValueError,TypeError) as e:
        raise ValueError(f'{nombre}: ingresa un número entero.') from e
    if not minimo<=n<=maximo:
        raise ValueError(f'{nombre}: debe estar entre {minimo} y {maximo}.')
    return n

def minuto(v):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',str(v)):
        raise ValueError('Hora inválida. Usa HH:MM.')
    h,m=map(int,v.split(':'));return h*60+m

def hora(n):
    return f'{n//60:02d}:{n%60:02d}'

def generar(form,actor,dias):
    db=get_db()
    profesional=entero(form.get('profesional_id'),'Funcionario',1,10**9)
    tipo=entero(form.get('tipo_id'),'Tipo de atención',1,10**9)
    desde=date.fromisoformat(fecha_iso(form.get('desde'),'Fecha inicial'))
    hasta=date.fromisoformat(fecha_iso(form.get('hasta'),'Fecha final'))
    if desde.isoformat()<hoy() or hasta<desde or (hasta-desde).days>30:
        raise ValueError('Elige fechas desde hoy, en un rango de hasta 31 días.')
    inicio=minuto(form.get('inicio'));fin=minuto(form.get('fin'))
    minutos=entero(form.get('minutos'),'Minutos por atención',5,240)
    cupos=entero(form.get('cupos'),'Cupos por bloque',1,20)
    if fin<=inicio:
        raise ValueError('La hora final debe ser posterior a la inicial.')
    dias={entero(d,'Día de semana',0,6) for d in dias}
    if not dias:
        raise ValueError('Selecciona al menos un día de la semana.')
    pausa=None
    if form.get('pausa_inicio') or form.get('pausa_fin'):
        pausa=(minuto(form.get('pausa_inicio')),minuto(form.get('pausa_fin')))
        if not inicio<=pausa[0]<pausa[1]<=fin:
            raise ValueError('La pausa debe estar dentro de la jornada.')
    bloques=[]
    fecha=desde
    while fecha<=hasta:
        if fecha.weekday() in dias:
            for a in range(inicio,fin-minutos+1,minutos):
                z=a+minutos
                if not pausa or not (a<pausa[1] and z>pausa[0]):
                    bloques.append((fecha.isoformat(),hora(a),hora(z)))
        fecha+=timedelta(days=1)
    if not bloques or len(bloques)>500:
        raise ValueError('La configuración debe generar entre 1 y 500 bloques completos.')
    with db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM profesionales WHERE id=? AND activo=1',(profesional,)).fetchone():
            raise ValueError('Funcionario no disponible.')
        if not db.execute('SELECT 1 FROM tipos_atencion WHERE id=? AND activo=1',(tipo,)).fetchone():
            raise ValueError('Tipo de atención no disponible.')
        for f,a,z in bloques:
            if db.execute('SELECT 1 FROM agenda_bloques WHERE profesional_id=? AND fecha=? AND activo=1 AND inicio<? AND fin>?',
                          (profesional,f,z,a)).fetchone():
                raise ConflictoAgenda(f'El funcionario ya tiene un horario que se cruza el {f}, entre {a} y {z}. No se creó ningún bloque.')
        for f,a,z in bloques:
            c=db.execute('INSERT INTO agenda_bloques(profesional_id,tipo_id,fecha,inicio,fin,cupos,creado_por) VALUES(?,?,?,?,?,?,?)',
                         (profesional,tipo,f,a,z,cupos,actor))
            evento(db,actor,'agenda_creada',c.lastrowid,'agenda')
    return len(bloques)

def validar_reserva(db,slot,paciente,excluir=None):
    if not slot or not slot['profesional_activo'] or slot['fecha']<hoy():
        raise ValueError('El horario no está disponible o pertenece a una fecha pasada.')
    if not paciente or not paciente['activo']:
        raise ValueError('El paciente no está activo.')
    if slot['fecha']<paciente['nacimiento']:
        raise ValueError('La cita no puede ser anterior al nacimiento.')
    ocupados=db.execute("SELECT COUNT(*) FROM admisiones WHERE slot_id=? AND activo=1 AND estado!='cancelado' AND (? IS NULL OR id!=?)",(slot['id'],excluir,excluir)).fetchone()[0]
    if ocupados>=slot['cupos']:
        raise ConflictoAgenda('Este horario ya no tiene cupos disponibles.')
    if db.execute("""SELECT 1 FROM admisiones a JOIN agenda_bloques b ON b.id=a.slot_id
        WHERE a.paciente_id=? AND a.activo=1 AND a.estado!='cancelado' AND b.fecha=? AND b.inicio<? AND b.fin>?
        AND (? IS NULL OR a.id!=?)""",(paciente['id'],slot['fecha'],slot['fin'],slot['inicio'],excluir,excluir)).fetchone():
        raise ConflictoAgenda('El paciente ya tiene una cita en un horario que se cruza.')

def reservar(slot_id,paciente_id,motivo,actor,admision_id=None):
    db=get_db()
    motivo=texto(motivo,'Motivo',500)
    with db:
        db.execute('BEGIN IMMEDIATE')
        slot=AgendaModel.obtener(slot_id)
        paciente=db.execute('SELECT * FROM pacientes WHERE id=?',(paciente_id,)).fetchone()
        existente=None
        if admision_id:
            existente=db.execute('SELECT * FROM admisiones WHERE id=? AND activo=1',(admision_id,)).fetchone()
            if not existente or existente['paciente_id']!=paciente_id or existente['estado']!='pendiente' or existente['slot_id'] is not None:
                raise ValueError('Solo puedes agendar una admisión pendiente sin horario del paciente elegido.')
        validar_reserva(db,slot,paciente,admision_id)
        if existente:
            db.execute('UPDATE admisiones SET slot_id=?,profesional_id=?,fecha=?,especialidad=?,motivo=?,version=version+1 WHERE id=?',
                (slot_id,slot['profesional_id'],slot['fecha'],slot['especialidad'],motivo,admision_id))
            id=admision_id
        else:
            import time
            c=db.execute('INSERT INTO admisiones(paciente_id,profesional_id,fecha,especialidad,motivo,creado_por,creada,slot_id) VALUES(?,?,?,?,?,?,?,?)',
                (paciente_id,slot['profesional_id'],slot['fecha'],slot['especialidad'],motivo,actor,int(time.time()),slot_id))
            id=c.lastrowid
        evento(db,actor,'cita_reservada',id,'admision')
    return id

def reprogramar(id,slot_id,version,actor):
    db=get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        a=db.execute('SELECT * FROM admisiones WHERE id=? AND activo=1',(id,)).fetchone()
        if not a or a['slot_id'] is None or a['estado'] not in ('pendiente','cancelado') or a['version']!=version:
            raise ConflictoAgenda('La cita cambió o ya no puede reprogramarse.')
        slot=AgendaModel.obtener(slot_id)
        paciente=db.execute('SELECT * FROM pacientes WHERE id=?',(a['paciente_id'],)).fetchone()
        validar_reserva(db,slot,paciente,id)
        db.execute("UPDATE admisiones SET slot_id=?,profesional_id=?,fecha=?,especialidad=?,estado='pendiente',version=version+1 WHERE id=?",
            (slot_id,slot['profesional_id'],slot['fecha'],slot['especialidad'],id))
        evento(db,actor,'cita_reprogramada',id,'admision')
