import os
import secrets
from pathlib import Path
from flask import Flask, session, request, abort, render_template
from .models.database import init_db

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
                      DATABASE=str(Path(app.instance_path) / 'clinica.sqlite'),
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      MAX_CONTENT_LENGTH=1024*1024)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_db(app)
    @app.before_request
    def proteger_formularios():
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method == 'POST':
            if not secrets.compare_digest(session['csrf'], request.form.get('csrf', '')):
                abort(400, description='Formulario vencido o inválido. Recarga la página.')
    from .controllers.clinica_controller import bp
    app.register_blueprint(bp)
    @app.errorhandler(404)
    def no_encontrado(error):
        return render_template('error.html', titulo='Ficha no encontrada', mensaje='El paciente no existe o fue eliminado.'), 404
    @app.errorhandler(500)
    def error_interno(error):
        return render_template('error.html', titulo='No se pudo abrir esta página', mensaje='Revisa el error en la terminal donde ejecutaste run.py.'), 500
    return app
