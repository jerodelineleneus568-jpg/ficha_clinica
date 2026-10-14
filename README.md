# Agenda y documentos externos

Consulta **AGENDA.md** para actualizar y crear agendas, reservar citas, parametrizar rendimiento y adjuntar documentos.

# Ficha clínica · Funcionarios, pacientes, roles y admisión

Consulta primero **ADMISION.md** para actualizar y usar el CRUD, la lista de espera y Excel.

# Ficha clínica Flask MVC con roles y HTTPS

Consulta `SEGURIDAD.md`: contiene instalación, creación del administrador, roles, certificados, OWASP y comandos de auditoría.

## Inicio Ubuntu
```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
bash scripts/crear_certificado.sh
venv/bin/python -m flask --app run crear-admin
venv/bin/python run.py
```
Abre https://172.24.189.179:8443/login con certificado local de confianza. En SSH reenvía puerto 8443. No existe cuenta ni contraseña predeterminada.

MVC: modelos en app/models, controladores en app/controllers, vistas en app/templates y estilos en app/static. SQLite guarda pacientes, profesionales, atenciones, usuarios, sesiones e historial de auditoría. Las migraciones preservan las tablas anteriores.

Primero entra como administrador para crear cuentas y asociarlas a profesionales. Recepción registra pacientes. Los profesionales registran atenciones con su propia identidad. El auditor revisa eventos. Seis profesionales ficticios se cargan una sola vez.

Esta versión desactiva pacientes, conservando historial. No ejecutes los actualizadores antiguos después de instalar seguridad, porque podrían reemplazar los controles por una versión anterior.

Prototipo local para datos ficticios, con controles probados. El uso institucional requiere las medidas pendientes descritas en SEGURIDAD.md y un despliegue apropiado.
