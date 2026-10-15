import hashlib
import time
from io import BytesIO
from pathlib import Path
from flask import Blueprint,abort,current_app,flash,g,redirect,render_template,request,send_file,url_for
from werkzeug.utils import secure_filename
from ..models.database import get_db
from ..models.clinica_model import PacienteModel
from ..security import roles_required,audit
from ..services.admision_service import texto,evento

bp=Blueprint('documento',__name__)
ROLES_DOCUMENTOS=('admin','recepcion','profesional','paciente')

def paciente_autorizado(id):
    if g.usuario['rol']=='paciente' and g.usuario['paciente_id']!=id:
        abort(404)
    p=PacienteModel.obtener(id)
    if not p:abort(404)
    return p

def documento_autorizado(id):
    doc=get_db().execute('SELECT id,paciente_id,nombre,descripcion,mime,tamano,sha256,creado_por,creada FROM documentos WHERE id=? AND activo=1',(id,)).fetchone()
    if not doc:abort(404)
    paciente_autorizado(doc['paciente_id'])
    return doc

def validar_archivo(file):
    if not file or not file.filename:
        raise ValueError('Selecciona un documento.')
    nombre=secure_filename(file.filename)[:150]
    ext=Path(nombre).suffix.lower()
    if ext not in ('.pdf','.png','.jpg','.jpeg'):
        raise ValueError('Solo se admiten PDF, PNG y JPG.')
    contenido=file.stream.read(current_app.config['DOC_MAX_SIZE']+1)
    if not contenido or len(contenido)>current_app.config['DOC_MAX_SIZE']:
        raise ValueError('El documento debe estar entre 1 byte y 5 MB.')
    if ext=='.pdf':
        valido=contenido.startswith(b'%PDF-') and b'%%EOF' in contenido[-2048:]
        mime='application/pdf'
    elif ext=='.png':
        valido=contenido.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in contenido[-16:]
        mime='image/png'
    else:
        valido=contenido.startswith(b'\xff\xd8\xff') and contenido.endswith(b'\xff\xd9')
        mime='image/jpeg'
    if not valido:
        raise ValueError('El contenido no coincide con el formato del documento.')
    return nombre,mime,contenido

@bp.route('/pacientes/<int:id>/documentos',methods=['GET','POST'])
@roles_required(*ROLES_DOCUMENTOS)
def listar(id):
    paciente=paciente_autorizado(id)
    if request.method=='POST':
        try:
            nombre,mime,contenido=validar_archivo(request.files.get('archivo'))
            descripcion=texto(request.form.get('descripcion'),'Descripción',300)
            db=get_db()
            with db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT COUNT(*) FROM documentos WHERE paciente_id=?',(id,)).fetchone()[0]>=100:
                    raise ValueError('Este paciente alcanzó el límite de 100 documentos acumulados.')
                por_paciente=db.execute('SELECT COALESCE(SUM(tamano),0) FROM documentos WHERE paciente_id=?',(id,)).fetchone()[0]
                total=db.execute('SELECT COALESCE(SUM(tamano),0) FROM documentos').fetchone()[0]
                if por_paciente+len(contenido)>current_app.config['DOC_PATIENT_QUOTA']:
                    raise ValueError('Este paciente alcanzó el límite de 25 MB de documentos, incluidos los retirados.')
                if total+len(contenido)>current_app.config['DOC_TOTAL_QUOTA']:
                    raise ValueError('Se alcanzó la capacidad de documentos de la aplicación. Contacta al administrador.')
                c=db.execute('INSERT INTO documentos(paciente_id,nombre,descripcion,mime,tamano,sha256,contenido,creado_por,creada) VALUES(?,?,?,?,?,?,?,?,?)',
                    (id,nombre,descripcion,mime,len(contenido),hashlib.sha256(contenido).hexdigest(),contenido,g.usuario['id'],int(time.time())))
                evento(db,g.usuario['id'],'documento_adjuntado',c.lastrowid,'documento')
            flash('Documento adjuntado a la ficha del paciente.', 'success')
            return redirect(url_for('documento.listar',id=id))
        except ValueError as e:flash(str(e), 'error')
    docs=get_db().execute('SELECT id,nombre,descripcion,tamano,creado_por,creada FROM documentos WHERE paciente_id=? AND activo=1 ORDER BY creada DESC,id DESC',(id,)).fetchall()
    return render_template('documentos.html',paciente=paciente,documentos=docs)

@bp.get('/documentos/<int:id>/descargar')
@roles_required('admin','profesional','paciente')
def descargar(id):
    doc=documento_autorizado(id)
    row=get_db().execute('SELECT contenido FROM documentos WHERE id=? AND activo=1',(id,)).fetchone()
    contenido=row['contenido']
    if hashlib.sha256(contenido).hexdigest()!=doc['sha256']:
        abort(409)
    audit('documento_descargado','documento',id)
    return send_file(BytesIO(contenido),as_attachment=True,download_name=doc['nombre'],mimetype=doc['mime'],max_age=0)

@bp.route('/documentos/<int:id>/editar',methods=['GET','POST'])
@roles_required(*ROLES_DOCUMENTOS)
def editar(id):
    doc=documento_autorizado(id)
    if g.usuario['rol']!='admin' and doc['creado_por']!=g.usuario['id']:
        abort(403)
    if request.method=='POST':
        try:
            descripcion=texto(request.form.get('descripcion'),'Descripción',300)
            db=get_db()
            with db:
                db.execute('UPDATE documentos SET descripcion=? WHERE id=? AND activo=1',(descripcion,id))
                evento(db,g.usuario['id'],'documento_editado',id,'documento')
            return redirect(url_for('documento.listar',id=doc['paciente_id']))
        except ValueError as e:flash(str(e), 'error')
    return render_template('documento_editar.html',documento=doc)

@bp.route('/documentos/<int:id>/eliminar',methods=['GET','POST'])
@roles_required(*ROLES_DOCUMENTOS)
def eliminar(id):
    doc=documento_autorizado(id)
    if g.usuario['rol']!='admin' and doc['creado_por']!=g.usuario['id']:
        abort(403)
    if request.method=='POST':
        if request.form.get('confirmar')!='ELIMINAR':flash('Escribe ELIMINAR para confirmar.', 'error')
        else:
            db=get_db()
            with db:
                db.execute('UPDATE documentos SET activo=0 WHERE id=?',(id,))
                evento(db,g.usuario['id'],'documento_retirado',id,'documento')
            return redirect(url_for('documento.listar',id=doc['paciente_id']))
    return render_template('documento_eliminar.html',documento=doc)
