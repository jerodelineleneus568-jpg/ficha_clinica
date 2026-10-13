# Ficha clínica · Python / Flask / MVC

Prototipo educativo local. Usar únicamente datos ficticios. No incluye autenticación ni permisos; registrar un profesional no crea una cuenta de acceso.

## Ejecutar en Visual Studio Code
1. Descomprime el proyecto y abre la carpeta `ficha_clinica` en VS Code.
2. Instala Python 3.10 o superior y la extensión Python de VS Code.
3. Abre Terminal → Nueva terminal.

### Windows (PowerShell)
```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe run.py
```
No es necesario activar el entorno ni modificar la política de PowerShell.

### Ubuntu / Linux
```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python run.py
```
Si Ubuntu no tiene venv: `sudo apt install python3-venv`.

4. Abre http://127.0.0.1:5000 en el navegador del mismo equipo donde ejecutaste Python.
5. Ya hay seis profesionales de ejemplo. Registra un paciente, presiona Ver ficha y guarda una atención.
6. Detén el servidor con Ctrl+C. Los registros permanecen al reiniciar.

Si trabajas por SSH, reenvía el puerto 5000 en la pestaña Puertos de VS Code y abre la dirección local reenviada.

## Funciones
- Crear, buscar y listar pacientes.
- Registrar profesionales con cargo y especialidad.
- Seis profesionales ficticios se agregan una sola vez al iniciar.
- Registrar varias atenciones de distintos profesionales para un mismo paciente.
- Consultar la ficha con historial ordenado por fecha.
- Eliminar pacientes mediante confirmación explícita (incluye sus atenciones).
- Evitar documentos repetidos, fechas futuras y profesionales inexistentes.

El documento se normaliza quitando puntos y espacios y convirtiéndolo a mayúsculas. No valida el dígito verificador del RUT. No incluye edición de pacientes en esta versión.

## Organización MVC
- Modelo: `app/models/`: base de datos y consultas parametrizadas.
- Vista: `app/templates/` y `app/static/`: páginas HTML y diseño.
- Controlador: `app/controllers/clinica_controller.py`: rutas, validaciones y coordinación.
- `app/__init__.py`: crea y configura la aplicación.
- `run.py`: punto de entrada.

Flask utiliza Jinja para las plantillas. Las carpetas organizan el proyecto según MVC; no se necesita un framework adicional.

## Base de datos
SQLite crea automáticamente `instance/clinica.sqlite` en la primera ejecución.

`pacientes (1) → atenciones (muchas) ← (1) profesionales`

Cada atención guarda paciente, profesional, fecha, motivo, diagnóstico y tratamiento. La relación paciente-profesional es de muchos a muchos a través de atenciones. Un paciente sin atenciones también puede existir.

## Pruebas
```bash
python -m unittest discover -s tests -v
```
En Windows usa `venv\Scripts\python.exe`; en Linux `venv/bin/python` en lugar de `python`.

## Alcance
El servidor escucha solo en el equipo local y no usa modo debug. Incluye protección CSRF y consultas parametrizadas. Para datos clínicos reales se requiere una versión con autenticación, permisos por rol, auditoría, HTTPS, copias de seguridad y políticas de conservación del historial. La eliminación definitiva implementada aquí es para el prototipo; su comportamiento debe definirse antes del uso clínico.

Documentación oficial: https://flask.palletsprojects.com/en/stable/quickstart/

## Actualizar una instalación anterior en Ubuntu
Detén el servidor con Ctrl+C. Copia `actualizar_ficha.py` en tu carpeta remota `~/ficha_clinica` usando el explorador de VS Code (SSH), y ejecuta:
```bash
cd ~/ficha_clinica
python3 actualizar_ficha.py
venv/bin/python -m pip install -r requirements.txt
venv/bin/python run.py
```
El actualizador hace una copia de seguridad del código y de la base de datos en una carpeta `respaldo_...`. Actualiza código y plantillas, sin sustituir `instance/clinica.sqlite` ni el entorno virtual. Al iniciar Flask se agrega la columna cargo a la base antigua sin borrar registros.

Si Ver ficha sigue mostrando un error, comprueba que la dirección cambió a `/pacientes/NUMERO` y lee el mensaje de la terminal. Guarda todos los archivos y reinicia el proceso correcto. No se ha inspeccionado el código instalado en tu máquina: esta distribución contiene todos los archivos completos para evitar plantillas vacías o faltantes.
# ficha_clinica
