# Agenda por profesional, citas y documentos externos

## Instalar la actualización

1. Detén el servidor con Ctrl+C.
2. Copia el actualizador nuevo junto al run.py principal, fuera de carpetas respaldo, y guarda el archivo.
3. Ejecuta en Ubuntu:

```bash
cd ~/ficha_clinica
python3 actualizar_ficha.py
venv/bin/python -m pip install -r requirements.txt
venv/bin/python run.py
```

El mensaje debe indicar **Versión con agenda, citas y documentos externos instalada**. El actualizador respalda el código y SQLite y conserva cuentas, pacientes, admisiones, atenciones, documentos y certificados. Captura la IP y los hosts permitidos de los archivos principales existentes y los guarda en `instance/network.json`. La migración se aplica al iniciar la aplicación.

Continúa usando tu dirección HTTPS actual. Si Ubuntu cambió de IP, consulta `hostname -I` y ejecuta temporalmente `FICHA_HOST=IP_ACTUAL venv/bin/python run.py`. Este valor también se agrega a los hosts permitidos. Después actualiza network.json y el certificado para que incluya esa IP en su SAN. No cambies a un host que escuche todas las interfaces; utiliza una IP concreta o localhost. La clave privada permanece en certs y no se entrega con esta distribución.

## Crear una agenda

Administrador o recepción → Agenda → Crear agenda.

- Profesional: el funcionario que atenderá.
- Tipo de atención: consulta general, control, primera consulta, evaluación o un tipo creado por el administrador.
- Fecha inicial/final: desde hoy, máximo 31 días por generación.
- Días de semana: días en que trabaja dentro del rango.
- Inicio y fin de jornada: por ejemplo 08:00 a 13:00.
- Duración: entre 5 y 240 minutos por bloque. Selecciona el número que necesitas; la opción del tipo muestra un valor sugerido.
- Cupos: entre 1 y 20 pacientes por bloque.
- Pausa opcional: se omiten los bloques que se cruzan con ella.

Se crean solo bloques completos. Un horario ya creado para ese profesional no puede cruzarse con otro, aunque sea de un tipo distinto. Si se detecta un cruce no se crea ningún bloque del lote. Máximo 500 bloques por generación.

Ejemplo: 08:00–10:00, duración 60 minutos y 1 cupo crea dos bloques: 08:00–09:00 y 09:00–10:00. Duración 30 minutos crea cuatro bloques. Para atención individual deja un cupo por bloque. Cupos superiores a uno representan una atención grupal con pacientes compartiendo el mismo horario.

## Rendimiento y disponibilidad

Rendimiento programado = 60 × cupos por bloque / duración en minutos.

| Duración | Cupos por bloque | Capacidad programada |
|---|---|---|
| 60 minutos | 1 | 1 paciente/hora |
| 30 minutos | 1 | 2 pacientes/hora |
| 20 minutos | 1 | 3 pacientes/hora |
| 60 minutos | 4 | 4 pacientes/hora, modalidad grupal |

Es capacidad nominal de la agenda, no una medición de duración real de la atención. El listado muestra total de cupos, ocupados y disponibles para el filtro aplicado. Las citas atendidas también consumen su cupo histórico; no se vuelve a vender un cupo ya atendido.

## Reservar y atender

1. Agenda → filtra fecha, profesional y tipo → Citar paciente en un bloque disponible.
2. Selecciona un paciente registrado y el motivo. El paciente se registra previamente en Pacientes si no existe.
3. Puedes crear una nueva admisión para la cita o vincular una admisión pendiente sin horario del mismo paciente. Al vincular se toman la fecha, el profesional y la especialidad del bloque.
4. La cita se guarda como admisión pendiente y aparece con fecha, hora y tipo en Admisión y en Mis admisiones del paciente.
5. La cuenta profesional vinculada a ese funcionario consulta Agenda → Ver citas → Atender, o Admisión → Atender.
6. Iniciar atención cambia a en atención; Guardar y finalizar crea el registro clínico y cambia a atendido.

Un paciente puede tener varias citas futuras, siempre que sus horarios no se crucen. Se mantiene el límite anterior de una admisión abierta sin horario. La reserva usa una transacción con bloqueo de escritura y vuelve a comprobar cupos y cruces antes de guardar, evitando sobreventa concurrente.

La agenda admite reservas para el día actual aunque el bloque sea de una hora anterior; sirve para registrar actividad del mismo día. No permite nuevas reservas para fechas pasadas. Las citas futuras no pueden iniciarse antes de su fecha; en el día de la cita se permite iniciar a cualquier hora. No incluye recordatorios, asistencia/no asistencia, lista de espera automática ni notificaciones por correo.

## Reprogramar, cancelar y editar

- Ver citas → Reprogramar: elige un bloque con cupos en los próximos 31 días. Puede cambiar de profesional y tipo, sin cruces de horario del paciente.
- Ver citas → Cancelar cita: una cita pendiente pasa a cancelada y libera el cupo. Requiere confirmación.
- Citas en atención o atendidas no se cancelan ni reprograman desde esta versión.
- Editar bloque: modifica horas y cupos. Con reservas solo se permite ajustar cupos sin bajar del total ocupado; para cambiar horas primero reprograma las citas.
- Eliminar bloque: eliminación lógica; solo si no tiene citas vigentes o atendidas que consuman cupos. Conserva las referencias de las citas canceladas.
- Los cambios detectan versiones obsoletas para evitar que un formulario antiguo sobreescriba una modificación reciente.
- Tipos de atención: el administrador crea, edita y desactiva tipos. Cambiar sus valores sugeridos no altera duración ni cupos de bloques existentes.

## Documentos que trae el paciente

Pacientes → Ver ficha → Documentos externos. También hay acceso desde la pantalla de atención. El portal paciente tiene Mis documentos externos.

1. Escribe una descripción, por ejemplo “Examen de laboratorio recibido de otro centro”.
2. Selecciona PDF, JPG o PNG.
3. Presiona Adjuntar documento.

- Máximo 5 MB por documento, 25 MB y 100 documentos acumulados por paciente; cuota total de archivos de la aplicación 250 MB.
- Se validan extensión, firma básica, tamaño y nombre; se calcula SHA-256 para comprobar integridad al descargar. No es una validación estructural completa del archivo ni un análisis antivirus. Para operación institucional añade análisis antimalware y políticas de retención.
- Los documentos se guardan dentro de SQLite, fuera de las rutas públicas, y quedan incluidos en el respaldo de la base.
- Se descargan como adjuntos, sin vista previa embebida ni ejecución en el servidor.
- Administrador y profesionales pueden descargarlos dentro del alcance clínico del centro. Recepción puede cargarlos y consultar metadatos, pero no descargar el contenido.
- Paciente: carga/consulta/descarga únicamente sus propios documentos; no accede a documentos de otras fichas.
- Administrador o usuario que cargó el documento pueden editar su descripción y retirarlo del listado. Retirar conserva datos y trazabilidad y no libera la cuota acumulada.
- Un paciente desactivado pierde acceso; la conservación del historial y documentos no depende de que conserve una cuenta activa.

No adjuntes archivos reales durante las pruebas. La base y los respaldos requieren cifrado de disco y control de acceso institucional, descritos en SEGURIDAD.md.

## Permisos

| Acción | Admin | Recepción | Profesional | Paciente | Auditor |
|---|---|---|---|---|---|
| Crear/editar/eliminar bloques | Sí | Sí | No | No | No |
| Crear/editar/desactivar tipos | Sí | No | No | No | No |
| Reservar/reprogramar/cancelar | Sí | Sí | No | No | No |
| Consultar agenda completa | Sí | Sí | Solo propia | No | No |
| Ver sus citas | No | No | Solo asignadas | Solo propias | No |
| Adjuntar documentos | Sí | Sí | Sí | Solo propios | No |
| Descargar documentos | Sí | No | Sí, alcance clínico del centro | Solo propios | No |
| Editar/retirar documentos | Sí | Solo los cargados por su cuenta | Solo los cargados por su cuenta | Solo los cargados por su cuenta | No |

El acceso de profesionales a fichas y documentos sigue siendo por centro, como en la versión anterior; no es una restricción por médico tratante para las fichas históricas. Agenda y citas sí se limitan al profesional asignado.

## Verificar

```bash
venv/bin/python -m unittest discover -s tests -v
bash scripts/auditar.sh
```

La evidencia de esta versión distingue pruebas automatizadas y SAST/SCA de los análisis ZAP, que deben repetirse con las nuevas rutas. La aplicación permanece como prototipo de desarrollo; una operación institucional requiere despliegue WSGI/proxy, revisión de políticas clínicas, retención, copias de seguridad probadas, MFA y monitoreo.
