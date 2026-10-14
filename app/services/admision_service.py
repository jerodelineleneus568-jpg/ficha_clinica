from datetime import date, datetime
import time
from ..models.database import get_db

ESTADOS=('pendiente','en_atencion','atendido','cancelado')

def texto(valor,nombre,maximo=200,obligatorio=True):
    v=str(valor or '').strip()
    if (obligatorio and not v) or len(v)>maximo:
        raise ValueError(f'{nombre}: obligatorio y máximo {maximo} caracteres.')
    return v

def fecha_iso(valor,nombre):
    if isinstance(valor,(datetime,date)):
        return valor.date().isoformat() if isinstance(valor,datetime) else valor.isoformat()
    try:
        return date.fromisoformat(str(valor).strip()).isoformat()
    except ValueError as e:
        raise ValueError(f'{nombre}: utiliza AAAA-MM-DD.') from e

def datos_paciente(form):
    doc=texto(form.get('documento'),'Documento',40).replace('.','').replace(' ','').upper()
    if not doc:
        raise ValueError('Documento vacío.')
    nombre=texto(form.get('nombre'),'Nombre')
    nacimiento=fecha_iso(form.get('nacimiento'),'Nacimiento')
    if nacimiento>date.today().isoformat():
        raise ValueError('El nacimiento no puede ser futuro.')
    telefono=texto(form.get('telefono'),'Teléfono',40,False)
    correo=texto(form.get('correo'),'Correo',200,False)
    if correo and ('@' not in correo or any(c.isspace() for c in correo)):
        raise ValueError('Correo inválido.')
    return (doc,nombre,nacimiento,telefono,correo)

def validar_admision(datos,paciente):
    fecha=fecha_iso(datos.get('fecha'),'Fecha de admisión')
    if fecha<paciente['nacimiento']:
        raise ValueError('La fecha no puede ser anterior al nacimiento.')
    especialidad=texto(datos.get('especialidad'),'Especialidad',100)
    motivo=texto(datos.get('motivo'),'Motivo',500)
    profesional=datos.get('profesional_id')
    try:
        profesional=int(profesional) if profesional not in (None,'') else None
    except (ValueError,TypeError) as e:
        raise ValueError('Profesional inválido.') from e
    if profesional:
        db=get_db()
        p=db.execute('SELECT * FROM profesionales WHERE id=? AND activo=1',(profesional,)).fetchone()
        if not p:
            raise ValueError('El funcionario seleccionado no está activo.')
        if p['especialidad'].casefold()!=especialidad.casefold():
            raise ValueError('La especialidad debe coincidir con la del funcionario seleccionado.')
    return (profesional,fecha,especialidad,motivo)

def evento(db,actor,accion,referencia,entidad='admision'):
    db.execute('INSERT INTO auditoria(usuario_id,accion,entidad,referencia,fecha) VALUES(?,?,?,?,?)',
               (actor,accion,entidad,referencia,int(time.time())))

def insertar_admision(db,paciente_id,valores,actor):
    c=db.execute('INSERT INTO admisiones(paciente_id,profesional_id,fecha,especialidad,motivo,creado_por,creada) VALUES(?,?,?,?,?,?,?)',
                 (paciente_id,*valores,actor,int(time.time())))
    evento(db,actor,'admision_creada',c.lastrowid)
    return c.lastrowid
