import sqlite3
import click
from flask.cli import with_appcontext
from .models.database import get_db
from .models.usuario_model import crear_usuario
from .security import audit

def register_cli(app):
    @app.cli.command('crear-admin')
    @with_appcontext
    def crear_admin():
        """Crea el primer administrador sin contraseñas predeterminadas."""
        if get_db().execute("SELECT 1 FROM usuarios WHERE rol='admin' AND activo=1").fetchone():
            raise click.ClickException('Ya existe un administrador. Utiliza el módulo Usuarios.')
        username=click.prompt('Nombre de usuario',default='admin')
        nombre=click.prompt('Nombre completo')
        password=click.prompt('Contraseña (mínimo 12 caracteres)',hide_input=True,confirmation_prompt=True)
        try:
            id=crear_usuario(username,nombre,password,'admin')
            audit('admin_inicial_creado','usuario',id,actor=id)
        except (ValueError,sqlite3.IntegrityError) as e:
            raise click.ClickException(str(e)) from e
        click.echo('Administrador creado correctamente.')
