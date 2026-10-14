import hashlib
import secrets
import time
from functools import wraps
from flask import abort, g, redirect, request, session, url_for
from .models.database import get_db

ROLES = ('admin', 'recepcion', 'profesional', 'auditor', 'paciente')

def audit(accion, entidad='', referencia=None, actor=None):
    db = get_db()
    usuario = actor if actor is not None else (g.usuario['id'] if getattr(g, 'usuario', None) else None)
    with db:
        db.execute('INSERT INTO auditoria(usuario_id,accion,entidad,referencia,fecha) VALUES(?,?,?,?,?)',
                   (usuario, accion, entidad, referencia, int(time.time())))

def roles_required(*roles):
    def decorate(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for('auth.login'))
            if g.usuario['rol'] not in roles:
                audit('acceso_denegado', 'ruta')
                abort(403)
            return func(*args, **kwargs)
        return wrapped
    return decorate

def cargar_usuario():
    g.usuario = None
    sid = session.get('sid')
    if not sid:
        return
    digest = hashlib.sha256(sid.encode()).hexdigest()
    now = int(time.time())
    db = get_db()
    row = db.execute("""SELECT u.id,u.nombre,u.username,u.rol,u.profesional_id,u.paciente_id,
        s.creada,s.ultima FROM sesiones s JOIN usuarios u ON u.id=s.usuario_id
        WHERE s.token_hash=? AND u.activo=1""", (digest,)).fetchone()
    if row is None or now-row['ultima'] > 900 or now-row['creada'] > 28800:
        with db:
            db.execute('DELETE FROM sesiones WHERE token_hash=?', (digest,))
        session.clear()
        return
    if row['rol'] in ('paciente','profesional'):
        tabla = 'pacientes' if row['rol']=='paciente' else 'profesionales'
        id = row['paciente_id'] if row['rol']=='paciente' else row['profesional_id']
        activo = db.execute('SELECT activo FROM pacientes WHERE id=?' if tabla=='pacientes' else 'SELECT activo FROM profesionales WHERE id=?',(id,)).fetchone()
        if not activo or not activo['activo']:
            with db:
                db.execute('DELETE FROM sesiones WHERE token_hash=?',(digest,))
            session.clear()
            return
    g.usuario = row
    with db:
        db.execute('UPDATE sesiones SET ultima=? WHERE token_hash=?', (now,digest))

def iniciar_sesion(usuario):
    cerrar_sesion()
    sid = secrets.token_urlsafe(32)
    now = int(time.time())
    db = get_db()
    with db:
        db.execute('DELETE FROM sesiones WHERE creada < ? OR ultima < ?', (now-28800,now-900))
        db.execute('INSERT INTO sesiones(token_hash,usuario_id,creada,ultima) VALUES(?,?,?,?)',
                   (hashlib.sha256(sid.encode()).hexdigest(),usuario['id'],now,now))
    session.clear()
    session['sid'] = sid
    session['csrf'] = secrets.token_urlsafe(32)
    session.permanent = True

def cerrar_sesion():
    sid = session.get('sid')
    if sid:
        db = get_db()
        with db:
            db.execute('DELETE FROM sesiones WHERE token_hash=?', (hashlib.sha256(sid.encode()).hexdigest(),))
    session.clear()
