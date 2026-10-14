# Funcionarios, pacientes y admisión

## Dos grupos y sus roles

Funcionarios: cuentas de administrador, recepción, profesional y auditor. Los funcionarios que atienden tienen un registro en Funcionarios (nombre, cargo, especialidad) y una cuenta de rol profesional vinculada a ese registro.

Pacientes: fichas administrativas y clínicas. No necesitan una contraseña para ser ingresados a admisión. Si deben entrar al sistema, el administrador crea una cuenta de rol paciente y la vincula a su ficha. Esa cuenta solo consulta sus propias admisiones; no ve otros pacientes, fichas clínicas, diagnósticos, funcionarios ni auditoría.

| Módulo / acción | Admin | Recepción | Profesional | Paciente | Auditor |
|---|---|---|---|---|---|
| Registro de pacientes: crear/editar | Sí | Sí | No | No | No |
| Desactivar paciente | Sí | No | No | No | No |
| Listado de funcionarios | Sí | Sí | Sí | No | No |
| Funcionarios: crear/editar/desactivar | Sí | No | No | No | No |
| Admisión: crear/editar/eliminar/importar/exportar | Sí | Sí | No | No | No |
| Admisiones asignadas e iniciar/finalizar | No | No | Sí, solo propias | No | No |
| Mis admisiones | No | No | No | Sí, solo propias | No |
| Historial clínico | Sí | No | Sí | No | No |
| Cuentas: crear/editar/desactivar | Sí | No | No | No | No |
| Auditoría | Sí | No | No | No | Sí |

## Actualizar en tu Ubuntu

Detén el servidor, descarga el actualizador nuevo y reemplaza `actualizar_ficha.py` junto al run.py principal. No trabajes dentro de carpetas respaldo.

```bash
cd ~/ficha_clinica
python3 actualizar_ficha.py
venv/bin/python -m pip install -r requirements.txt
venv/bin/python run.py
```

Se conserva SQLite, los usuarios, los pacientes, los certificados y las atenciones. La migración añade paciente_id a usuarios y crea la tabla admisiones. La configuración de red actual se conserva en instance/network.json; consulta AGENDA.md. Debe ser una IP vigente de Ubuntu (`hostname -I`). Utiliza https://172.24.189.179:8443/login. Si la IP cambia, ajusta run.py, TRUSTED_HOSTS y el SAN del certificado.

El administrador existente sigue funcionando: no hace falta crearlo nuevamente. Si es una instalación nueva, crea venv, genera certificados con `bash scripts/crear_certificado.sh` y ejecuta `venv/bin/python -m flask --app run crear-admin` antes de iniciar. Los certificados existentes no se reemplazan automáticamente.

## Uso paso a paso

1. Entra como administrador. En Funcionarios registra o revisa nombre, cargo y especialidad. Hay seis ejemplos ficticios.
2. En Usuarios crea cuentas de rol profesional y vincula cada cuenta al funcionario correspondiente. Crea recepción si es necesario. La edición de cuentas permite modificar rol, vínculo y contraseña; revoca sesiones y no deja al sistema sin administrador.
3. Recepción entra a Admisión → Nueva admisión. Puede seleccionar un paciente existente o crear uno nuevo con documento, nombre, nacimiento, teléfono y correo.
4. Registra fecha, especialidad, motivo y funcionario. La especialidad debe coincidir con la del funcionario. Puede dejarlo sin asignar y editar después.
5. El listado muestra quién espera, fecha, estado y responsable. Un profesional solo ve sus admisiones asignadas. Una cuenta vinculada a un funcionario desactivado no puede mantener sesión.
6. El profesional selecciona Atender → Iniciar atención. El estado cambia a en atención.
7. Completa motivo, diagnóstico y tratamiento y selecciona Guardar y finalizar. La admisión queda atendida y se agrega la atención a la ficha del paciente, con la identidad del profesional de esa cuenta. Esta operación es una transacción: estado, atención y auditoría se guardan juntos.
8. El mismo paciente puede tener otra admisión con otro funcionario cuando la anterior ya esté atendida o cancelada. Puede mantener una admisión abierta sin horario, y varias citas agendadas si no se cruzan.
9. Si el paciente necesita acceso, en Usuarios crea una cuenta paciente vinculada a su ficha. Al entrar verá Mis admisiones, con sus estados, fechas y funcionario asignado. No existe autorregistro público.

## CRUD y conservación

- Pacientes: crear/listar/ver/editar/desactivar. Una desactivación cancela sus admisiones pendientes, desactiva su cuenta y conserva el historial. No se desactiva durante una atención en curso.
- Funcionarios: crear/listar/editar/desactivar. No se desactiva ni cambia su especialidad mientras tenga admisiones abiertas; primero deben reasignarse o completarse. Desactivar también desactiva su cuenta vinculada.
- Usuarios: crear/listar/editar/activar/desactivar. Cada profesional/paciente puede tener una sola cuenta vinculada. Los cambios cierran sus sesiones.
- Admisiones: crear/listar/editar/eliminar. Edición y eliminación solo para pendiente/cancelado. Eliminación lógica: se retira del listado, conservando trazabilidad. Las admisiones en atención y atendidas se protegen para no alterar el historial.
- Los formularios de admisión detectan versiones obsoletas: si otro usuario cambió el registro, se pide recargar antes de guardar.

## Excel nativo .xlsx

Admisión → Importar Excel → Descargar plantilla. Es un libro Excel real, no un CSV renombrado. Tiene una sola hoja y estos encabezados, en este orden:

| Columna | Contenido |
|---|---|
| documento | RUT u otro documento como texto |
| nombre | Nombre completo |
| nacimiento | AAAA-MM-DD o celda de fecha Excel |
| telefono | Opcional, como texto |
| correo | Opcional |
| fecha | Fecha de admisión, AAAA-MM-DD o fecha Excel |
| especialidad | Especialidad de atención |
| motivo | Motivo del ingreso, hasta 500 caracteres |
| profesional_id | ID de Funcionarios; opcional si se asignará después |

Cada fila es un paciente y su admisión. No se crean cuentas de usuario desde Excel. Máximo 1000 filas y 2 MB de archivo, sujeto al límite total de la solicitud. No se admiten fórmulas, archivos con macros, columnas extra ni hojas adicionales. Se limita el tamaño descomprimido del ZIP y se utiliza defusedxml para el XML.

Pacientes existentes se reconocen por documento, nombre y nacimiento. Sus datos no se sobrescriben; una discrepancia se informa por fila. Si hay una fila inválida, no se importa ninguna: se muestra hasta 30 errores para corregir. Reimportar un paciente con una admisión abierta tampoco duplica datos.

Exportar listado a Excel descarga las admisiones que coinciden con los filtros de búsqueda/estado. Las celdas de texto se guardan como texto para evitar fórmulas inyectadas. El exportado tiene columnas de listado y no sustituye la plantilla de importación.

## Pruebas y seguridad

```bash
venv/bin/python -m unittest discover -s tests -v
bash scripts/auditar.sh
```

Las nuevas pruebas cubren CRUD, importación válida, rechazo completo del lote, fórmulas, estados, concurrencia de versión, separación de pacientes, vinculación de cuentas y dos profesionales atendiendo al mismo paciente. Las pruebas anteriores de seguridad se conservan. La guía SEGURIDAD.md explica HTTPS, herramientas y límites. Los resultados previos no validan automáticamente esta nueva versión: consulta la evidencia actualizada.

Prototipo para pruebas con datos ficticios. Antes del uso institucional deben definirse despliegue WSGI/proxy, cifrado del disco, MFA, respaldo/restauración, monitoreo y reglas de acceso clínico por centro. Esta versión incorpora agenda horaria y cupos en AGENDA.md; no incluye notificaciones ni recordatorios.
