import re
from werkzeug.security import generate_password_hash
from .database import get_db
from ..security import ROLES

def validar_usuario(username,nombre,rol,profesional_id=None,paciente_id=None):
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9_.-]{3,50}',username):
        raise ValueError('Usuario: entre 3 y 50 caracteres, letras minúsculas, números, punto, guion o guion bajo.')
    if not nombre.strip() or len(nombre)>200:
        raise ValueError('Ingresa un nombre de hasta 200 caracteres.')
    if rol not in ROLES:
        raise ValueError('Rol inválido.')
    db = get_db()
    if rol == 'profesional':
        if not profesional_id or not db.execute('SELECT 1 FROM profesionales WHERE id=? AND activo=1',(profesional_id,)).fetchone():
            raise ValueError('Asocia la cuenta a un profesional registrado.')
        paciente_id = None
    elif rol == 'paciente':
        profesional_id = None
        if not paciente_id or not db.execute('SELECT 1 FROM pacientes WHERE id=? AND activo=1',(paciente_id,)).fetchone():
            raise ValueError('Asocia la cuenta a un paciente activo.')
    else:
        profesional_id = None
        paciente_id = None
    return username,nombre.strip(),rol,profesional_id,paciente_id

def crear_usuario(username,nombre,password,rol,profesional_id=None,paciente_id=None):
    username,nombre,rol,profesional_id,paciente_id=validar_usuario(username,nombre,rol,profesional_id,paciente_id)
    if not 12<=len(password)<=128:
        raise ValueError('La contraseña debe tener entre 12 y 128 caracteres.')
    db=get_db()
    with db:
        c = db.execute('INSERT INTO usuarios(username,nombre,password_hash,rol,profesional_id,paciente_id) VALUES(?,?,?,?,?,?)',
            (username,nombre.strip(),generate_password_hash(password,method='scrypt'),rol,profesional_id,paciente_id))
    return c.lastrowid
