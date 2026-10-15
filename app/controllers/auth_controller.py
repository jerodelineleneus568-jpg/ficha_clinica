import hashlib
import hmac
import secrets
import sqlite3
import time
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from ..models.database import get_db
from ..models.usuario_model import crear_usuario
from ..models.clinica_model import ProfesionalModel, PacienteModel
from ..security import audit, cerrar_sesion, iniciar_sesion, roles_required, ROLES

bp = Blueprint('auth',__name__)
# Hash de un valor aleatorio para igualar el trabajo cuando el usuario no existe.
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32),method='scrypt')

def destino(rol):
    return url_for('ui.inicio')

@bp.route('/login',methods=['GET','POST'])
def login():
    if g.usuario:
        return redirect(destino(g.usuario['rol']))
    if request.method == 'POST':
        username = request.form.get('username','').strip().lower()[:50]
        password = request.form.get('password','')
        if len(password)>128:
            abort(400)
        now = int(time.time())
        db = get_db()
        # Límites por cuenta y por dirección. No se guardan identificadores en claro.
        claves = [hmac.new(current_app.secret_key.encode(),v.encode(),hashlib.sha256).hexdigest()
                  for v in ('user:'+username,'ip:'+(request.remote_addr or 'unknown'))]
        for clave,limite in zip(claves,(5,20)):
            row=db.execute('SELECT * FROM intentos WHERE clave=?',(clave,)).fetchone()
            if row and now-row['desde']<300 and row['fallos']>=limite:
                audit('login_bloqueado','usuario')
                abort(429)
        u=db.execute('SELECT * FROM usuarios WHERE username=?',(username,)).fetchone()
        valido=check_password_hash(u['password_hash'] if u else DUMMY_HASH,password)
        if u is None or not u['activo'] or not valido:
            with db:
                db.execute('DELETE FROM intentos WHERE desde < ?',(now-300,))
                for clave in claves:
                    db.execute("""INSERT INTO intentos(clave,fallos,desde) VALUES(?,1,?)
                        ON CONFLICT(clave) DO UPDATE SET fallos=fallos+1""",(clave,now))
            audit('login_fallido','usuario')
            flash('Usuario o contraseña incorrectos.')
            return render_template('login.html'),401
        with db:
            db.execute('DELETE FROM intentos WHERE clave=?',(claves[0],))
        iniciar_sesion(u)
        audit('login_correcto','usuario',u['id'],actor=u['id'])
        return redirect(destino(u['rol']))
    return render_template('login.html')

@bp.post('/logout')
@roles_required(*ROLES)
def logout():
    audit('logout','usuario',g.usuario['id'])
    cerrar_sesion()
    return redirect(url_for('auth.login'))

@bp.route('/usuarios',methods=['GET','POST'])
@roles_required('admin')
def usuarios():
    if request.method == 'POST':
        try:
            id_prof=request.form.get('profesional_id','')
            id_prof=int(id_prof) if id_prof else None
            id_pac=request.form.get('paciente_id','')
            id_pac=int(id_pac) if id_pac else None
            id=crear_usuario(request.form.get('username',''),request.form.get('nombre',''),
                request.form.get('password',''),request.form.get('rol',''),id_prof,id_pac)
            audit('usuario_creado','usuario',id)
            flash('Usuario creado. Entrega su contraseña por un canal seguro.', 'success')
            return redirect(url_for('auth.usuarios'))
        except ValueError as e:
            flash(str(e), 'error')
        except sqlite3.IntegrityError:
            flash('El usuario o profesional ya tiene una cuenta.')
    users=get_db().execute('SELECT id,username,nombre,rol,activo FROM usuarios ORDER BY nombre').fetchall()
    return render_template('usuarios.html',usuarios=users,profesionales=ProfesionalModel.listar(),pacientes=PacienteModel.listar(),roles=ROLES)

@bp.post('/usuarios/<int:id>/estado')
@roles_required('admin')
def estado_usuario(id):
    if id==g.usuario['id']:
        abort(400)
    db=get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        u=db.execute('SELECT * FROM usuarios WHERE id=?',(id,)).fetchone()
        if not u:
            abort(404)
        if u['rol']=='admin' and u['activo']:
            if db.execute("SELECT COUNT(*) FROM usuarios WHERE rol='admin' AND activo=1").fetchone()[0]<=1:
                abort(400)
        db.execute('UPDATE usuarios SET activo=? WHERE id=?',(0 if u['activo'] else 1,id))
        db.execute('DELETE FROM sesiones WHERE usuario_id=?',(id,))
    audit('usuario_estado_cambiado','usuario',id)
    return redirect(url_for('auth.usuarios'))

@bp.route('/password',methods=['GET','POST'])
@roles_required(*ROLES)
def password():
    if request.method=='POST':
        db=get_db()
        u=db.execute('SELECT * FROM usuarios WHERE id=?',(g.usuario['id'],)).fetchone()
        anterior=request.form.get('anterior','')
        nueva=request.form.get('nueva','')
        if len(anterior)>128 or not check_password_hash(u['password_hash'],anterior):
            flash('La contraseña actual no es correcta.')
        elif not 12<=len(nueva)<=128 or nueva==anterior:
            flash('Elige una contraseña distinta de entre 12 y 128 caracteres.')
        else:
            with db:
                db.execute('UPDATE usuarios SET password_hash=? WHERE id=?',
                    (generate_password_hash(nueva,method='scrypt'),u['id']))
                db.execute('DELETE FROM sesiones WHERE usuario_id=?',(u['id'],))
            audit('password_cambiada','usuario',u['id'])
            cerrar_sesion()
            return redirect(url_for('auth.login'))
    return render_template('password.html')

@bp.get('/auditoria')
@roles_required('admin','auditor')
def auditoria():
    audit('auditoria_consultada','auditoria')
    eventos=get_db().execute("""SELECT a.*,u.username FROM auditoria a LEFT JOIN usuarios u ON u.id=a.usuario_id
        ORDER BY a.id DESC LIMIT 500""").fetchall()
    return render_template('auditoria.html',eventos=eventos)

@bp.route('/usuarios/<int:id>/editar',methods=['GET','POST'])
@roles_required('admin')
def editar_usuario(id):
    from ..models.usuario_model import validar_usuario
    from ..services.admision_service import evento
    db=get_db()
    u=db.execute('SELECT * FROM usuarios WHERE id=?',(id,)).fetchone()
    if not u:
        abort(404)
    if request.method=='POST':
        try:
            pid=request.form.get('profesional_id','')
            pac=request.form.get('paciente_id','')
            vals=validar_usuario(request.form.get('username',''),request.form.get('nombre',''),request.form.get('rol',''),int(pid) if pid else None,int(pac) if pac else None)
            nueva=request.form.get('password','')
            if nueva and not 12<=len(nueva)<=128:
                raise ValueError('La contraseña debe tener entre 12 y 128 caracteres.')
            with db:
                db.execute('BEGIN IMMEDIATE')
                u=db.execute('SELECT * FROM usuarios WHERE id=?',(id,)).fetchone()
                if id==g.usuario['id'] and vals[2]!='admin':
                    raise ValueError('No puedes quitarte el rol de administrador.')
                if u['activo'] and u['rol']=='admin' and vals[2]!='admin' and db.execute("SELECT COUNT(*) FROM usuarios WHERE activo=1 AND rol='admin'").fetchone()[0]<=1:
                    raise ValueError('Debe mantenerse al menos un administrador activo.')
                db.execute('UPDATE usuarios SET username=?,nombre=?,rol=?,profesional_id=?,paciente_id=? WHERE id=?',(*vals,id))
                if nueva:
                    db.execute('UPDATE usuarios SET password_hash=? WHERE id=?',(generate_password_hash(nueva,method='scrypt'),id))
                db.execute('DELETE FROM sesiones WHERE usuario_id=?',(id,))
                evento(db,g.usuario['id'],'usuario_editado',id,'usuario')
            flash('Usuario actualizado. Debe iniciar sesión nuevamente.', 'success')
            return redirect(url_for('auth.login') if id==g.usuario['id'] else url_for('auth.usuarios'))
        except ValueError as e:
            flash(str(e), 'error')
        except sqlite3.IntegrityError:
            flash('El usuario, paciente o profesional ya tiene una cuenta vinculada.')
    return render_template('editar_usuario.html',usuario=u,roles=ROLES,pacientes=PacienteModel.listar(),profesionales=ProfesionalModel.listar())
