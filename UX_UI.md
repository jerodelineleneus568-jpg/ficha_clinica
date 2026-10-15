# Mejoras UX y UI de la ficha clínica

## Qué cambia

UX (experiencia de uso) organiza las tareas para que sea fácil saber qué hacer. UI (interfaz visual) presenta esas tareas con una apariencia consistente.

- Inicio según el rol: resumen del día y accesos a Agenda, Admisión y Pacientes; pacientes y auditores tienen accesos propios.
- Menú lateral con módulo activo, identificación de cuenta y profesional, y navegación móvil.
- Jerarquía visual, espacios, tipografía, botones y estados con texto además del color.
- Crear agenda muestra pasos orientativos y una vista previa de bloques/cupos. Cambiar el tipo completa su duración y cupos sugeridos; se pueden modificar. La vista previa no reserva ni confirma disponibilidad: el servidor comprueba los cruces al guardar.
- La admisión oculta los datos de un paciente nuevo al elegir uno existente y completa la especialidad al seleccionar al funcionario.
- Los roles muestran solo la asociación necesaria; la validación de permisos sigue en el servidor.
- Al reservar, el selector filtra las admisiones según el paciente elegido. Los conflictos indican la cita y el horario existentes.
- Avisos de error y confirmación diferenciados, explicación de listados vacíos y enlaces para limpiar filtros.
- Documentos: ayuda con formatos y tamaño antes de enviar. El servidor mantiene su propia validación.
- Mostrar/ocultar contraseña, enlace para saltar al contenido, foco visible y formularios con etiquetas.

No se afirma conformidad completa con WCAG. Quedan pendientes pruebas con usuarios reales y tecnologías de asistencia. Las ayudas JavaScript son progresivas: el servidor conserva las reglas y las validaciones.

## Instalar sobre la aplicación existente

1. Detener Flask con Ctrl+C.
2. Guardar el nuevo actualizar_ficha.py en /home/jerodeline/ficha_clinica, junto al run.py principal.
3. Ejecutar desde esa carpeta:

```bash
python3 actualizar_ficha.py
venv/bin/python -m pip install -r requirements.txt
venv/bin/python run.py
```

Debe aparecer: `Versión con mejoras UX y UI instalada.` El actualizador respalda los archivos que reemplaza y la base SQLite. Conserva datos, certificados y configuración de red. No debe ejecutarse dentro de respaldos. Reiniciar con las mismas variables de entorno de red que se usaban previamente.

Ingresar con una cuenta existente y abrir Inicio. Actualizar el navegador con Ctrl+F5 si conserva estilos antiguos. No es necesario volver a crear usuarios.

## Validación

Consultar evidencia_validacion/UX_UI.md y tests.log. El script opcional scripts/verificar_interfaz.py requiere Playwright y Chromium, usa una base temporal y no se ejecuta en producción. Las capturas usadas durante la revisión no contienen datos reales ni se distribuyen.

Los controles de HTTPS, sesiones, CSRF y permisos se mantienen. CSP permite JavaScript externo del propio origen sin habilitar scripts en línea. Los informes anteriores de seguridad conservan su alcance y fecha; esta revisión de interfaz no constituye una nueva auditoría OWASP ni un análisis DAST.
