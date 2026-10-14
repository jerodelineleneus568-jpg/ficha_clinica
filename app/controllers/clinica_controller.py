import sqlite3
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from ..security import roles_required, audit
from flask import g
from ..models.clinica_model import PacienteModel, ProfesionalModel, AtencionModel

bp = Blueprint('clinica', __name__)

def campo(nombre, maximo=200, obligatorio=True):
    valor = request.form.get(nombre, '').strip()
    if (obligatorio and not valor) or len(valor) > maximo:
        raise ValueError(f'Revisa el campo {nombre}: obligatorio y máximo {maximo} caracteres.')
    return valor

def fecha(nombre):
    try:
        valor = date.fromisoformat(campo(nombre, 10))
    except ValueError:
        raise ValueError('Ingresa una fecha válida.')
    if valor > date.today():
        raise ValueError('La fecha no puede ser futura.')
    return valor.isoformat()

@bp.get('/')
@roles_required('admin','recepcion','profesional')
def index():
    q = request.args.get('q', '').strip()[:200]
    return render_template('pacientes.html', pacientes=PacienteModel.listar(q), q=q)

@bp.route('/pacientes/nuevo', methods=['GET','POST'])
@roles_required('admin','recepcion')
def nuevo_paciente():
    if request.method == 'POST':
        try:
            documento = campo('documento', 40).replace('.', '').replace(' ', '').upper()
            if not documento:
                raise ValueError('Ingresa un documento válido.')
            id = PacienteModel.crear((documento, campo('nombre'), fecha('nacimiento'),
                                     campo('telefono',40,False), campo('correo',200,False)))
            audit('paciente_creado','paciente',id)
            flash('Paciente registrado correctamente.')
            return redirect(url_for('clinica.ficha', id=id))
        except sqlite3.IntegrityError:
            flash('Ya existe un paciente con ese documento.')
        except ValueError as e:
            flash(str(e))
    return render_template('nuevo_paciente.html')

@bp.get('/pacientes/<int:id>')
@roles_required('admin','recepcion','profesional')
def ficha(id):
    paciente = PacienteModel.obtener(id)
    if paciente is None:
        abort(404)
    audit('ficha_consultada','paciente',id)
    clinico = g.usuario['rol'] in ('admin','profesional')
    return render_template('ficha.html', paciente=paciente, atenciones=AtencionModel.listar(id) if clinico else [],
        profesionales=ProfesionalModel.listar() if clinico else [], hoy=date.today().isoformat())

@bp.post('/pacientes/<int:id>/atenciones')
@roles_required('profesional')
def nueva_atencion(id):
    if PacienteModel.obtener(id) is None:
        abort(404)
    try:
        profesional = g.usuario['profesional_id']
        enviado=request.form.get('profesional_id')
        if enviado is not None and enviado != str(profesional):
            abort(403)
        if ProfesionalModel.obtener(profesional) is None:
            raise ValueError('Selecciona un profesional registrado.')
        AtencionModel.crear((id, profesional, fecha('fecha'), campo('motivo',2000),
                            campo('diagnostico',4000), campo('tratamiento',4000)))
        audit('atencion_creada','paciente',id)
        flash('Atención registrada.')
    except ValueError as e:
        flash(str(e))
        return ficha(id)
    return redirect(url_for('clinica.ficha', id=id))

@bp.route('/pacientes/<int:id>/eliminar', methods=['GET','POST'])
@roles_required('admin')
def eliminar(id):
    paciente = PacienteModel.obtener(id)
    if paciente is None:
        abort(404)
    if request.method == 'POST':
        from ..models.database import get_db
        if get_db().execute("SELECT 1 FROM admisiones WHERE paciente_id=? AND activo=1 AND estado='en_atencion'",(id,)).fetchone():
            abort(409)
        if request.form.get('confirmar') != 'ELIMINAR':
            flash('Escribe ELIMINAR para confirmar.')
        else:
            PacienteModel.eliminar(id)
            audit('paciente_desactivado','paciente',id)
            flash('Paciente desactivado. El historial se conserva.')
            return redirect(url_for('clinica.index'))
    return render_template('eliminar.html', paciente=paciente)

@bp.route('/profesionales', methods=['GET','POST'])
@roles_required('admin','recepcion','profesional')
def profesionales():
    if request.method=='POST' and g.usuario['rol']!='admin':
        abort(403)
    if request.method == 'POST':
        try:
            ProfesionalModel.crear(campo('nombre'), campo('especialidad',100), campo('cargo',100))
            audit('profesional_creado','profesional')
            flash('Profesional registrado.')
            return redirect(url_for('clinica.profesionales'))
        except ValueError as e:
            flash(str(e))
    return render_template('profesionales.html', profesionales=ProfesionalModel.listar())

@bp.route('/pacientes/<int:id>/editar',methods=['GET','POST'])
@roles_required('admin','recepcion')
def editar_paciente(id):
    from ..models.database import get_db
    from ..services.admision_service import datos_paciente, evento
    paciente=PacienteModel.obtener(id)
    if not paciente:
        abort(404)
    if request.method=='POST':
        db=get_db()
        try:
            valores=datos_paciente(request.form)
            with db:
                db.execute('UPDATE pacientes SET documento=?,nombre=?,nacimiento=?,telefono=?,correo=? WHERE id=? AND activo=1',(*valores,id))
                evento(db,g.usuario['id'],'paciente_editado',id,'paciente')
            flash('Datos del paciente actualizados.')
            return redirect(url_for('clinica.ficha',id=id))
        except ValueError as e:
            flash(str(e))
        except sqlite3.IntegrityError:
            flash('El documento ya corresponde a otro paciente.')
    return render_template('editar_paciente.html',paciente=paciente)

@bp.route('/profesionales/<int:id>/editar',methods=['GET','POST'])
@roles_required('admin')
def editar_profesional(id):
    from ..models.database import get_db
    from ..services.admision_service import evento
    p=ProfesionalModel.obtener(id)
    if not p:
        abort(404)
    if request.method=='POST':
        db=get_db()
        try:
            valores=(campo('nombre'),campo('especialidad',100),campo('cargo',100))
            with db:
                # Evita cambiar la especialidad mientras mantiene una cola asignada.
                if valores[1].casefold()!=p['especialidad'].casefold() and db.execute("SELECT 1 FROM admisiones WHERE profesional_id=? AND activo=1 AND estado IN ('pendiente','en_atencion')",(id,)).fetchone():
                    raise ValueError('Primero reasigna o completa las admisiones de este funcionario.')
                db.execute('UPDATE profesionales SET nombre=?,especialidad=?,cargo=? WHERE id=?',(*valores,id))
                evento(db,g.usuario['id'],'funcionario_editado',id,'profesional')
            return redirect(url_for('clinica.profesionales'))
        except ValueError as e:
            flash(str(e))
    return render_template('editar_profesional.html',profesional=p)

@bp.route('/profesionales/<int:id>/eliminar',methods=['GET','POST'])
@roles_required('admin')
def eliminar_profesional(id):
    from ..models.database import get_db
    from ..services.admision_service import evento
    p=ProfesionalModel.obtener(id)
    if not p:
        abort(404)
    if request.method=='POST':
        db=get_db()
        if request.form.get('confirmar')!='ELIMINAR':
            flash('Escribe ELIMINAR para confirmar.')
        else:
            with db:
                if db.execute("SELECT 1 FROM admisiones WHERE profesional_id=? AND activo=1 AND estado IN ('pendiente','en_atencion')",(id,)).fetchone():
                    flash('Primero reasigna o completa las admisiones del funcionario.')
                else:
                    db.execute('UPDATE profesionales SET activo=0 WHERE id=?',(id,))
                    db.execute('UPDATE usuarios SET activo=0 WHERE profesional_id=?',(id,))
                    db.execute('DELETE FROM sesiones WHERE usuario_id IN (SELECT id FROM usuarios WHERE profesional_id=?)',(id,))
                    evento(db,g.usuario['id'],'funcionario_desactivado',id,'profesional')
                    return redirect(url_for('clinica.profesionales'))
    return render_template('eliminar_profesional.html',profesional=p)
