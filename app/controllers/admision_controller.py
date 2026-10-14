import sqlite3
from datetime import date
from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from ..models.database import get_db
from ..models.clinica_model import PacienteModel, ProfesionalModel
from ..models.admision_model import AdmisionModel
from ..security import roles_required, audit
from ..services.admision_service import ESTADOS, datos_paciente, validar_admision, insertar_admision, evento, texto
from ..services.excel_service import leer_excel, importar_filas, crear_excel, COLUMNAS

bp=Blueprint('admision',__name__)

def filas():
    q=request.args.get('q','').strip()[:200]
    estado=request.args.get('estado','')
    if estado and estado not in ESTADOS:
        abort(400)
    profesional=g.usuario['profesional_id'] if g.usuario['rol']=='profesional' else None
    return AdmisionModel.listar(q,estado,profesional_id=profesional)

@bp.get('/admisiones')
@roles_required('admin','recepcion','profesional')
def listar():
    return render_template('admisiones.html',admisiones=filas(),estados=ESTADOS)

@bp.get('/mis-admisiones')
@roles_required('paciente')
def mis_admisiones():
    audit('admisiones_propias_consultadas','paciente',g.usuario['paciente_id'])
    return render_template('mis_admisiones.html',admisiones=AdmisionModel.listar(paciente_id=g.usuario['paciente_id']))

@bp.get('/mis-admisiones/<int:id>')
@roles_required('paciente')
def propia(id):
    a=AdmisionModel.obtener(id)
    if not a or a['paciente_id']!=g.usuario['paciente_id']:
        abort(404)
    return render_template('mis_admisiones.html',admisiones=[a])

@bp.route('/admisiones/nueva',methods=['GET','POST'])
@roles_required('admin','recepcion')
def nueva():
    if request.method=='POST':
        db=get_db()
        try:
            with db:
                opcion=request.form.get('paciente_id','')
                if opcion:
                    p=PacienteModel.obtener(int(opcion))
                    if not p:
                        raise ValueError('Selecciona un paciente activo.')
                    id=p['id']
                else:
                    valores=datos_paciente(request.form)
                    p=db.execute('SELECT * FROM pacientes WHERE documento=?',(valores[0],)).fetchone()
                    if p:
                        raise ValueError('Ese paciente ya existe. Selecciónalo en el listado.')
                    c=db.execute('INSERT INTO pacientes(documento,nombre,nacimiento,telefono,correo) VALUES(?,?,?,?,?)',valores)
                    id=c.lastrowid
                    p=db.execute('SELECT * FROM pacientes WHERE id=?',(id,)).fetchone()
                    evento(db,g.usuario['id'],'paciente_creado',id,'paciente')
                insertar_admision(db,id,validar_admision(request.form,p),g.usuario['id'])
            flash('Paciente ingresado a admisión correctamente.')
            return redirect(url_for('admision.listar'))
        except (ValueError,TypeError) as e:
            flash(str(e))
        except sqlite3.IntegrityError:
            flash('El paciente ya tiene una admisión abierta o el documento está repetido.')
    return render_template('admision_form.html',admision=None,pacientes=PacienteModel.listar(),profesionales=ProfesionalModel.listar(),hoy=date.today().isoformat())

@bp.route('/admisiones/<int:id>/editar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def editar(id):
    a=AdmisionModel.obtener(id)
    if not a:
        abort(404)
    if a['slot_id'] is not None:
        return redirect(url_for('agenda.reprogramar_cita',id=id))
    if a['estado'] not in ('pendiente','cancelado') or not a['paciente_activo']:
        abort(409)
    if request.method=='POST':
        db=get_db()
        try:
            valores=validar_admision(request.form,PacienteModel.obtener(a['paciente_id']))
            estado=request.form.get('estado','pendiente')
            if estado not in ('pendiente','cancelado'):
                raise ValueError('Estado inválido para recepción.')
            version=int(request.form.get('version','0'))
            with db:
                c=db.execute("""UPDATE admisiones SET profesional_id=?,fecha=?,especialidad=?,motivo=?,estado=?,version=version+1
                    WHERE id=? AND version=? AND activo=1 AND estado IN ('pendiente','cancelado')""",(*valores,estado,id,version))
                if c.rowcount!=1:
                    abort(409)
                evento(db,g.usuario['id'],'admision_editada',id)
            flash('Admisión actualizada.')
            return redirect(url_for('admision.listar'))
        except ValueError as e:
            flash(str(e))
        except sqlite3.IntegrityError:
            flash('Ya existe otra admisión abierta para ese paciente.')
    return render_template('admision_form.html',admision=a,pacientes=[],profesionales=ProfesionalModel.listar(),hoy=date.today().isoformat())

@bp.route('/admisiones/<int:id>/eliminar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def eliminar(id):
    a=AdmisionModel.obtener(id)
    if not a:
        abort(404)
    if a['estado'] not in ('pendiente','cancelado'):
        abort(409)
    if request.method=='POST':
        if request.form.get('confirmar')!='ELIMINAR':
            flash('Escribe ELIMINAR para confirmar.')
        else:
            db=get_db()
            with db:
                c=db.execute("UPDATE admisiones SET activo=0,estado='cancelado',version=version+1 WHERE id=? AND estado IN ('pendiente','cancelado') AND version=?",(id,int(request.form.get('version','0'))))
                if c.rowcount!=1:
                    abort(409)
                evento(db,g.usuario['id'],'admision_eliminada',id)
            return redirect(url_for('admision.listar'))
    return render_template('admision_eliminar.html',admision=a)

@bp.route('/admisiones/<int:id>/atender',methods=['GET','POST'])
@roles_required('profesional')
def atender(id):
    a=AdmisionModel.obtener(id)
    if not a or a['profesional_id']!=g.usuario['profesional_id']:
        abort(404)
    if not a['paciente_activo'] or a['estado'] not in ('pendiente','en_atencion'):
        abort(409)
    if a['fecha']>date.today().isoformat():
        flash('Esta admisión está programada para una fecha futura.')
        return redirect(url_for('admision.listar'))
    if request.method=='POST':
        db=get_db()
        try:
            version=int(request.form.get('version','0'))
            accion=request.form.get('accion')
            if accion not in ('iniciar','finalizar'):
                abort(400)
            valores=None
            if accion=='finalizar':
                valores=(texto(request.form.get('motivo'),'Motivo',2000),texto(request.form.get('diagnostico'),'Diagnóstico',4000),texto(request.form.get('tratamiento'),'Indicaciones',4000))
            with db:
                nuevo='en_atencion' if accion=='iniciar' else 'atendido'
                origen='pendiente' if accion=='iniciar' else 'en_atencion'
                c=db.execute('UPDATE admisiones SET estado=?,version=version+1 WHERE id=? AND version=? AND estado=? AND profesional_id=? AND activo=1',
                    (nuevo,id,version,origen,g.usuario['profesional_id']))
                if c.rowcount!=1:
                    abort(409)
                if valores:
                    db.execute('INSERT INTO atenciones(paciente_id,profesional_id,fecha,motivo,diagnostico,tratamiento,admision_id) VALUES(?,?,?,?,?,?,?)',
                        (a['paciente_id'],g.usuario['profesional_id'],date.today().isoformat(),*valores,id))
                evento(db,g.usuario['id'],'atencion_iniciada' if accion=='iniciar' else 'atencion_finalizada',id)
            flash('Atención iniciada.' if accion=='iniciar' else 'Atención guardada en la ficha clínica.')
            return redirect(url_for('admision.atender',id=id) if accion=='iniciar' else url_for('admision.listar'))
        except ValueError as e:
            flash(str(e))
    return render_template('admision_atender.html',admision=a)

@bp.route('/admisiones/importar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def importar():
    errores=[]
    if request.method=='POST':
        file=request.files.get('archivo')
        if not file or not file.filename.lower().endswith('.xlsx'):
            errores=['Selecciona un archivo Excel .xlsx.']
        else:
            try:
                rows=leer_excel(file.stream)
                n=importar_filas(rows,g.usuario['id'])
                flash(f'{n} admisiones importadas. No se modificaron los datos de pacientes ya existentes.')
                return redirect(url_for('admision.listar'))
            except ValueError as e:
                errores=str(e).splitlines()
    return render_template('admision_importar.html',errores=errores)

@bp.get('/admisiones/plantilla.xlsx')
@roles_required('admin','recepcion')
def plantilla():
    return send_file(crear_excel(COLUMNAS,[],titulo='Admisiones'),as_attachment=True,download_name='plantilla_admisiones.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@bp.get('/admisiones/exportar.xlsx')
@roles_required('admin','recepcion')
def exportar():
    data=[[a['id'],a['documento'],a['nombre'],a['fecha'],a['especialidad'],a['funcionario'] or 'Sin asignar',a['estado'],a['motivo'],a['inicio'] or '',a['fin'] or '',a['tipo_atencion'] or ''] for a in filas()]
    audit('admisiones_exportadas','admision')
    return send_file(crear_excel(['id','documento','nombre','fecha','especialidad','funcionario','estado','motivo','hora_inicio','hora_fin','tipo_atencion'],data,titulo='Listado'),as_attachment=True,download_name='admisiones.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
