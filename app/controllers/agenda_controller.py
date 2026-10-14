import sqlite3
from datetime import date,timedelta
from flask import Blueprint,abort,flash,g,redirect,render_template,request,url_for
from ..models.database import get_db
from ..models.agenda_model import AgendaModel
from ..models.admision_model import AdmisionModel
from ..models.clinica_model import PacienteModel,ProfesionalModel
from ..services.agenda_service import generar,reservar,reprogramar,minuto,hoy,entero,ConflictoAgenda
from ..services.admision_service import texto,fecha_iso,evento
from ..security import roles_required

bp=Blueprint('agenda',__name__)

def filtros():
    desde=fecha_iso(request.args.get('desde',hoy()),'Desde')
    hasta=fecha_iso(request.args.get('hasta',(date.fromisoformat(desde)+timedelta(days=7)).isoformat()),'Hasta')
    if hasta<desde or (date.fromisoformat(hasta)-date.fromisoformat(desde)).days>31:
        raise ValueError('El listado permite hasta 32 días por búsqueda.')
    profesional=request.args.get('profesional_id','')
    tipo=request.args.get('tipo_id','')
    profesional=entero(profesional,'Funcionario',1,10**9) if profesional else None
    tipo=entero(tipo,'Tipo',1,10**9) if tipo else None
    if g.usuario['rol']=='profesional':
        profesional=g.usuario['profesional_id']
    return desde,hasta,profesional,tipo

@bp.get('/agenda')
@roles_required('admin','recepcion','profesional')
def listar():
    try:
        desde,hasta,prof,tipo=filtros()
    except ValueError as e:
        flash(str(e));return redirect(url_for('agenda.listar'))
    bloques=AgendaModel.listar(desde,hasta,prof,tipo)
    total=sum(b['cupos'] for b in bloques);ocupados=sum(b['ocupados'] for b in bloques)
    return render_template('agenda.html',bloques=bloques,desde=desde,hasta=hasta,profesionales=ProfesionalModel.listar(),tipos=AgendaModel.tipos(),total=total,ocupados=ocupados,minuto=minuto)

@bp.route('/agenda/generar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def generar_agenda():
    if request.method=='POST':
        try:
            n=generar(request.form,g.usuario['id'],request.form.getlist('dias'))
            flash(f'Agenda creada: {n} bloques y {n*int(request.form["cupos"])} cupos totales.')
            return redirect(url_for('agenda.listar',desde=request.form['desde'],hasta=request.form['hasta'],profesional_id=request.form['profesional_id']))
        except (ValueError,sqlite3.IntegrityError) as e:
            flash(str(e) if isinstance(e,ValueError) else 'No se pudo crear la agenda: configuración duplicada.')
    return render_template('agenda_generar.html',profesionales=ProfesionalModel.listar(),tipos=AgendaModel.tipos(),hoy=hoy())

@bp.route('/agenda/tipos',methods=['GET','POST'])
@roles_required('admin')
def tipos():
    if request.method=='POST':
        try:
            nombre=texto(request.form.get('nombre'),'Nombre',100)
            minutos=entero(request.form.get('minutos'),'Minutos',5,240)
            cupos=entero(request.form.get('cupos'),'Cupos',1,20)
            db=get_db()
            with db:
                c=db.execute('INSERT INTO tipos_atencion(nombre,minutos,cupos) VALUES(?,?,?)',(nombre,minutos,cupos))
                evento(db,g.usuario['id'],'tipo_atencion_creado',c.lastrowid,'tipo')
            return redirect(url_for('agenda.tipos'))
        except ValueError as e:
            flash(str(e))
        except sqlite3.IntegrityError:
            flash('Ese tipo ya existe, incluso si está desactivado.')
    return render_template('agenda_tipos.html',tipos=get_db().execute('SELECT * FROM tipos_atencion ORDER BY nombre').fetchall())

@bp.route('/agenda/tipos/<int:id>/editar',methods=['GET','POST'])
@roles_required('admin')
def editar_tipo(id):
    db=get_db();tipo=db.execute('SELECT * FROM tipos_atencion WHERE id=?',(id,)).fetchone()
    if not tipo:abort(404)
    if request.method=='POST':
        try:
            valores=(texto(request.form.get('nombre'),'Nombre',100),entero(request.form.get('minutos'),'Minutos',5,240),entero(request.form.get('cupos'),'Cupos',1,20),1 if request.form.get('activo')=='1' else 0)
            with db:
                db.execute('UPDATE tipos_atencion SET nombre=?,minutos=?,cupos=?,activo=? WHERE id=?',(*valores,id))
                evento(db,g.usuario['id'],'tipo_atencion_editado',id,'tipo')
            return redirect(url_for('agenda.tipos'))
        except ValueError as e:flash(str(e))
        except sqlite3.IntegrityError:flash('El nombre ya existe.')
    return render_template('agenda_tipo_editar.html',tipo=tipo)

def bloque_autorizado(id):
    b=AgendaModel.obtener(id)
    if not b:abort(404)
    if g.usuario['rol']=='profesional' and b['profesional_id']!=g.usuario['profesional_id']:
        abort(404)
    return b

@bp.get('/agenda/bloques/<int:id>')
@roles_required('admin','recepcion','profesional')
def detalle(id):
    b=bloque_autorizado(id)
    citas=get_db().execute("""SELECT a.*,p.nombre,p.documento FROM admisiones a JOIN pacientes p ON p.id=a.paciente_id
        WHERE a.slot_id=? AND a.activo=1 ORDER BY a.creada""",(id,)).fetchall()
    return render_template('agenda_detalle.html',bloque=b,citas=citas)

@bp.route('/agenda/bloques/<int:id>/reservar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def reservar_cita(id):
    b=bloque_autorizado(id)
    if request.method=='POST':
        try:
            pid=entero(request.form.get('paciente_id'),'Paciente',1,10**9)
            aid=request.form.get('admision_id','')
            aid=entero(aid,'Admisión',1,10**9) if aid else None
            reservar(id,pid,request.form.get('motivo'),g.usuario['id'],aid)
            flash('Cita reservada e ingresada a admisión.')
            return redirect(url_for('agenda.detalle',id=id))
        except ConflictoAgenda as e:flash(str(e))
        except ValueError as e:flash(str(e))
        except sqlite3.IntegrityError:flash('El paciente ya tiene esta cita reservada.')
    pendientes=get_db().execute("""SELECT a.id,p.nombre,p.documento FROM admisiones a JOIN pacientes p ON p.id=a.paciente_id
        WHERE a.activo=1 AND p.activo=1 AND a.estado='pendiente' AND a.slot_id IS NULL ORDER BY p.nombre""").fetchall()
    return render_template('agenda_reservar.html',bloque=b,pacientes=PacienteModel.listar(),pendientes=pendientes)

@bp.route('/agenda/bloques/<int:id>/editar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def editar_bloque(id):
    b=bloque_autorizado(id)
    if request.method=='POST':
        db=get_db()
        try:
            inicio=request.form.get('inicio');fin=request.form.get('fin')
            if not 5<=minuto(fin)-minuto(inicio)<=240:
                raise ValueError('El bloque debe durar entre 5 y 240 minutos.')
            cupos=entero(request.form.get('cupos'),'Cupos',1,20)
            version=entero(request.form.get('version'),'Versión',1,10**9)
            with db:
                db.execute('BEGIN IMMEDIATE')
                b=AgendaModel.obtener(id)
                if not b or b['version']!=version:abort(409)
                if b['fecha']<hoy():raise ValueError('No puedes editar un horario de una fecha pasada.')
                if b['ocupados'] and (inicio!=b['inicio'] or fin!=b['fin'] or cupos<b['ocupados']):
                    raise ValueError('Con citas reservadas solo puedes ajustar cupos sin bajar del total ocupado. Reprograma antes de cambiar horas.')
                if db.execute('SELECT 1 FROM agenda_bloques WHERE id!=? AND profesional_id=? AND fecha=? AND activo=1 AND inicio<? AND fin>?',(id,b['profesional_id'],b['fecha'],fin,inicio)).fetchone():
                    raise ValueError('El horario se cruza con otro bloque del funcionario.')
                db.execute('UPDATE agenda_bloques SET inicio=?,fin=?,cupos=?,version=version+1 WHERE id=?',(inicio,fin,cupos,id))
                evento(db,g.usuario['id'],'agenda_editada',id,'agenda')
            return redirect(url_for('agenda.detalle',id=id))
        except ValueError as e:flash(str(e))
    return render_template('agenda_editar.html',bloque=b)

@bp.route('/agenda/bloques/<int:id>/eliminar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def eliminar_bloque(id):
    b=bloque_autorizado(id)
    if request.method=='POST':
        db=get_db()
        if request.form.get('confirmar')!='ELIMINAR':flash('Escribe ELIMINAR para confirmar.')
        else:
            with db:
                db.execute('BEGIN IMMEDIATE')
                b=AgendaModel.obtener(id)
                if not b:abort(404)
                if b['ocupados']:
                    flash('No puedes eliminar un bloque con citas: cancela o reprograma las pendientes. El historial atendido se conserva.')
                else:
                    db.execute('UPDATE agenda_bloques SET activo=0,version=version+1 WHERE id=?',(id,))
                    evento(db,g.usuario['id'],'agenda_eliminada',id,'agenda')
                    return redirect(url_for('agenda.listar',desde=b['fecha'],hasta=b['fecha']))
    return render_template('agenda_eliminar.html',bloque=b)

@bp.route('/agenda/citas/<int:id>/reprogramar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def reprogramar_cita(id):
    a=AdmisionModel.obtener(id)
    if not a or a['slot_id'] is None:abort(404)
    if a['estado'] not in ('pendiente','cancelado'):abort(409)
    if request.method=='POST':
        try:
            reprogramar(id,entero(request.form.get('slot_id'),'Horario',1,10**9),entero(request.form.get('version'),'Versión',1,10**9),g.usuario['id'])
            flash('Cita reprogramada.');return redirect(url_for('admision.listar'))
        except ConflictoAgenda as e:flash(str(e))
        except ValueError as e:flash(str(e))
        except sqlite3.IntegrityError:flash('Ya existe una cita del paciente para ese bloque.')
    hasta=(date.fromisoformat(hoy())+timedelta(days=31)).isoformat()
    slots=[b for b in AgendaModel.listar(hoy(),hasta) if b['ocupados']<b['cupos']]
    return render_template('agenda_reprogramar.html',admision=a,bloques=slots)

@bp.route('/agenda/citas/<int:id>/cancelar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def cancelar_cita(id):
    a=AdmisionModel.obtener(id)
    if not a or a['slot_id'] is None:abort(404)
    if a['estado']!='pendiente':abort(409)
    if request.method=='POST':
        if request.form.get('confirmar')!='CANCELAR':flash('Escribe CANCELAR para confirmar.')
        else:
            db=get_db()
            with db:
                c=db.execute("UPDATE admisiones SET estado='cancelado',version=version+1 WHERE id=? AND version=? AND estado='pendiente' AND activo=1",(id,entero(request.form.get('version'),'Versión',1,10**9)))
                if c.rowcount!=1:abort(409)
                evento(db,g.usuario['id'],'cita_cancelada',id,'admision')
            flash('Cita cancelada. El cupo volvió a estar disponible.');return redirect(url_for('agenda.detalle',id=a['slot_id']))
    return render_template('agenda_cancelar.html',admision=a)
