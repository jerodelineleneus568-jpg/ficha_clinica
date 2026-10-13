import sqlite3
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
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
def index():
    q = request.args.get('q', '').strip()[:200]
    return render_template('pacientes.html', pacientes=PacienteModel.listar(q), q=q)

@bp.route('/pacientes/nuevo', methods=['GET','POST'])
def nuevo_paciente():
    if request.method == 'POST':
        try:
            documento = campo('documento', 40).replace('.', '').replace(' ', '').upper()
            if not documento:
                raise ValueError('Ingresa un documento válido.')
            id = PacienteModel.crear((documento, campo('nombre'), fecha('nacimiento'),
                                     campo('telefono',40,False), campo('correo',200,False)))
            flash('Paciente registrado correctamente.')
            return redirect(url_for('clinica.ficha', id=id))
        except sqlite3.IntegrityError:
            flash('Ya existe un paciente con ese documento.')
        except ValueError as e:
            flash(str(e))
    return render_template('nuevo_paciente.html')

@bp.get('/pacientes/<int:id>')
def ficha(id):
    paciente = PacienteModel.obtener(id)
    if paciente is None:
        abort(404)
    return render_template('ficha.html', paciente=paciente, atenciones=AtencionModel.listar(id),
                           profesionales=ProfesionalModel.listar(), hoy=date.today().isoformat())

@bp.post('/pacientes/<int:id>/atenciones')
def nueva_atencion(id):
    if PacienteModel.obtener(id) is None:
        abort(404)
    try:
        profesional = int(campo('profesional_id',20))
        if ProfesionalModel.obtener(profesional) is None:
            raise ValueError('Selecciona un profesional registrado.')
        AtencionModel.crear((id, profesional, fecha('fecha'), campo('motivo',2000),
                            campo('diagnostico',4000), campo('tratamiento',4000)))
        flash('Atención registrada.')
    except ValueError as e:
        flash(str(e))
        return ficha(id)
    return redirect(url_for('clinica.ficha', id=id))

@bp.route('/pacientes/<int:id>/eliminar', methods=['GET','POST'])
def eliminar(id):
    paciente = PacienteModel.obtener(id)
    if paciente is None:
        abort(404)
    if request.method == 'POST':
        if request.form.get('confirmar') != 'ELIMINAR':
            flash('Escribe ELIMINAR para confirmar.')
        else:
            PacienteModel.eliminar(id)
            flash('Paciente y sus atenciones eliminados.')
            return redirect(url_for('clinica.index'))
    return render_template('eliminar.html', paciente=paciente)

@bp.route('/profesionales', methods=['GET','POST'])
def profesionales():
    if request.method == 'POST':
        try:
            ProfesionalModel.crear(campo('nombre'), campo('especialidad',100), campo('cargo',100))
            flash('Profesional registrado.')
            return redirect(url_for('clinica.profesionales'))
        except ValueError as e:
            flash(str(e))
    return render_template('profesionales.html', profesionales=ProfesionalModel.listar())
