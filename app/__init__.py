import os
import secrets
from datetime import timedelta
from pathlib import Path
from flask import Flask, g, session, request, abort, render_template
from werkzeug.exceptions import HTTPException, SecurityError
from .models.database import init_db
from .security import cargar_usuario

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    instance = Path(app.instance_path)
    instance.mkdir(parents=True, exist_ok=True)
    instance.chmod(0o700)
    secret = os.environ.get('SECRET_KEY')
    if not secret:
        archivo = instance / 'secret.key'
        try:
            with archivo.open('x', encoding='utf-8') as f:
                archivo.chmod(0o600)
                f.write(secrets.token_hex(32))
        except FileExistsError:
            archivo.chmod(0o600)
        secret = archivo.read_text().strip()
    if len(secret) < 32:
        raise RuntimeError('SECRET_KEY debe tener al menos 32 caracteres.')
    app.config.update(SECRET_KEY=secret, DATABASE=str(instance/'clinica.sqlite'),
        SESSION_COOKIE_NAME='__Host-ficha', SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_PATH='/', PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=2*1024*1024, MAX_FORM_MEMORY_SIZE=32768, MAX_FORM_PARTS=30,
        REQUIRE_HTTPS=True, TRUSTED_HOSTS=['localhost','127.0.0.1','[::1]','172.24.189.179'])
    if test_config:
        app.config.update(test_config)
    init_db(app)
    if not app.config.get('TESTING'):
        Path(app.config['DATABASE']).chmod(0o600)
    @app.before_request
    def seguridad():
        g.usuario = None
        if app.config['REQUIRE_HTTPS'] and not request.is_secure:
            abort(400, description='Utiliza HTTPS en el puerto 8443.')
        cargar_usuario()
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method == 'POST':
            if not secrets.compare_digest(session['csrf'].encode(), request.form.get('csrf', '').encode()):
                abort(400, description='Formulario vencido o inválido. Recarga la página.')
    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'none'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cache-Control'] = 'no-store'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response
    from .controllers.clinica_controller import bp
    from .controllers.auth_controller import bp as auth_bp
    app.register_blueprint(bp)
    app.register_blueprint(auth_bp)
    from .controllers.admision_controller import bp as admision_bp
    app.register_blueprint(admision_bp)
    from .cli import register_cli
    register_cli(app)
    @app.errorhandler(HTTPException)
    def http_error(error):
        if isinstance(error, SecurityError):
            return 'Host no permitido.', 400
        mensajes = {400:'Solicitud inválida. Recarga la página y utiliza HTTPS.',
            403:'Tu rol no tiene permiso para esta acción.',404:'No se encontró este recurso.',
            405:'Método no permitido.',409:'El registro cambió o ya está en atención. Recarga el listado.',413:'El formulario supera el tamaño permitido.',
            429:'Demasiados intentos. Espera cinco minutos.'}
        return render_template('error.html',titulo=f'Error {error.code}',
            mensaje=mensajes.get(error.code,'No se pudo procesar la solicitud.')), error.code
    @app.errorhandler(500)
    def server_error(error):
        return render_template('error.html',titulo='No se pudo completar la operación',
            mensaje='Contacta al administrador. No se guardó una operación incompleta.'),500
    return app
