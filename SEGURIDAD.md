# Agenda y documentos: actualización de seguridad

Consulta AGENDA.md para las rutas nuevas, permisos, límites de adjuntos y la configuración de red conservada. La solicitud admite hasta 6 MB, con límites propios de 5 MB para documentos y 2 MB para Excel. Los archivos se descargan como adjuntos y no se analizan con antivirus en esta versión.

# Seguridad de la ficha clínica

**Actualización de admisión:** consulta ADMISION.md para el nuevo rol paciente, CRUD y las reglas de importación. Esta versión escucha en 172.24.189.179:8443.

# Ficha clínica: roles, HTTPS y revisión de seguridad

Esta distribución incorpora controles, no una certificación de seguridad ni de cumplimiento clínico. Las revisiones se deben repetir en la máquina que aloja la aplicación. Usa datos ficticios para los análisis activos.

## Roles y permisos aplicados en el servidor

| Acción | Administrador | Recepción | Profesional | Auditor |
|---|---|---|---|---|
| Listar pacientes y ver datos administrativos | Sí | Sí | Sí | No |
| Registrar pacientes | Sí | Sí | No | No |
| Leer historial clínico | Sí | No | Sí | No |
| Registrar atención | No | No | Sí, con su propia identidad | No |
| Desactivar pacientes | Sí | No | No | No |
| Registrar profesionales | Sí | No | No | No |
| Crear/desactivar usuarios | Sí | No | No | No |
| Consultar auditoría | Sí | No | No | Sí |
| Cambiar contraseña propia | Sí | Sí | Sí | Sí |

Los profesionales pueden consultar las fichas activas del mismo centro de esta aplicación, para permitir atención por distintos profesionales. No hay separación por centros ni asignación individual de pacientes; si tu institución exige esa restricción, debe añadirse antes de usar datos reales. Un registro de profesional no es una cuenta: el administrador debe crear un usuario con rol profesional y asociarlo a ese registro. El profesional no puede indicar otro profesional al registrar una atención.

La desactivación sustituye el borrado físico de pacientes. Oculta la ficha activa y conserva las atenciones; no hay restauración desde la interfaz en esta versión. Los usuarios desactivados pierden sus sesiones inmediatamente. El administrador inicial es exclusivo; no puede desactivarse a sí mismo.

## Instalación / actualización en Ubuntu

1. Detén el servidor con Ctrl+C.
2. Copia `actualizar_ficha.py` en `~/ficha_clinica`, junto a run.py, mediante VS Code conectado por SSH.
3. Ejecuta:

```bash
cd ~/ficha_clinica
python3 actualizar_ficha.py
venv/bin/python -m pip install -r requirements.txt
bash scripts/crear_certificado.sh
venv/bin/python -m flask --app run crear-admin
venv/bin/python run.py
```

El comando crear-admin pregunta usuario, nombre y contraseña (mínimo 12 caracteres), sin mostrarla. No hay contraseña predeterminada. Si ya existe un administrador activo, el comando no crea otro: usa Usuarios. El actualizador respalda código y SQLite antes de escribir y no reemplaza tus datos, certificados o entorno virtual. La migración agrega tablas de seguridad y el indicador activo.

4. Para esta versión abre **https://172.24.189.179:8443/login** desde el equipo que tiene acceso a la red de la VM. Ya no requiere el reenvío del puerto para este acceso directo.
5. El certificado es local y autofirmado: el navegador no confía automáticamente en él. Copia solo `certs/cert.pem` al equipo cliente, comprueba su huella (`openssl x509 -in certs/cert.pem -noout -fingerprint -sha256`) e impórtalo como certificado de confianza de tu entorno de prueba. Nunca copies key.pem a otros equipos ni desactives globalmente la validación TLS. El script de certificados nuevos incluye SAN localhost, 127.0.0.1, ::1 y 172.24.189.179 y dura 90 días. Los certificados anteriores se conservan: verifica que incluyan la IP antes de usar acceso directo.
6. Ingresa como administrador → Usuarios → crea las cuentas. Para profesional elige uno de los registros demo, o registra un profesional primero. Crea cuentas para recepción y auditoría si las necesitas. Entrega claves por un canal seguro y pide cambiar su contraseña.
7. Inicia sesión con cada profesional para registrar sus atenciones al mismo paciente. Recepción no recibirá el texto clínico en el HTML.

TLS mínimo 1.2, cookies Secure/HttpOnly/SameSite=Lax, CSP, HSTS, no-store y rechazo de Host no permitido. HTTP se rechaza; no se sirve un puerto HTTP separado. Esta distribución permite la IP de tu VM y escucha en ella; limita el acceso a tu red de pruebas autorizada. El servidor Flask incluido es para desarrollo en una red de pruebas autorizada; un servicio institucional permanente requiere un servidor WSGI y un proxy TLS configurados y revisados. No lo publiques en Internet.

## Autenticación y sesiones

- Contraseñas almacenadas como hashes scrypt, nunca en claro.
- Token de sesión aleatorio; en SQLite se guarda su SHA-256. La cookie firmada contiene identificador y CSRF, no datos clínicos.
- Rol y estado consultados desde SQLite en cada solicitud, sin confiar en campos del navegador.
- Sesión: 15 minutos sin actividad y máximo 8 horas.
- Cinco fallos por cuenta o veinte por dirección en cinco minutos activan el bloqueo temporal. No se revela si el usuario existe. La misma IP compartida puede provocar bloqueo de varios usuarios.
- CSRF en todos los POST, incluidos login y logout; regeneración de sesión al autenticar.
- Cambio de contraseña y desactivación revocan todas las sesiones de esa cuenta.
- Usuarios con contraseñas de 12–128 caracteres; no hay autorregistro público.

## OWASP Top 10:2025 — controles y límites

Se utiliza la edición 2025 publicada por OWASP. No mezcles sus números con los de 2021.

| Riesgo | Medida aplicada | Evidencia / límite |
|---|---|---|
| A01 Control de acceso | Roles en rutas, lectura clínica restringida, identidad clínica desde la cuenta | Tests de accesos directos y suplantación; acceso de profesionales por centro |
| A02 Configuración | Debug apagado, Host permitido, límites de formulario, cabeceras y permisos de archivos | Tests y curl; revisar servidor institucional |
| A03 Cadena de suministro | Dependencias fijadas y pip-audit | SCA; los paquetes no están fijados con hashes de distribución |
| A04 Criptografía | HTTPS TLS 1.2+, claves aleatorias, scrypt | OpenSSL/curl; SQLite y respaldos NO están cifrados en reposo |
| A05 Inyección | Consultas parametrizadas y escape automático de Jinja | SAST y prueba XSS; sin eval/exec en aplicación |
| A06 Diseño inseguro | Permisos mínimos, bloqueo, desactivación conservando historial | Tests; requiere revisión del flujo institucional |
| A07 Autenticación | Hashes, sesiones expirables/revocables y límites de intentos | Tests; no incluye MFA ni recuperación de claves por correo |
| A08 Integridad | CSRF, FK, transacciones SQLite y auditoría protegida contra UPDATE/DELETE | Tests; acceso al archivo SQLite permite alterar controles, sin firma externa |
| A09 Registro y alertas | Login, accesos, cambios y denegaciones auditados sin texto clínico | Vista auditoría; no hay alertas externas/SIEM todavía |
| A10 Condiciones excepcionales | Errores genéricos, rollback de operaciones DB y límites de entrada | Tests de datos inválidos; servidor no expone trazas al navegador |

Las escrituras de datos y la escritura posterior del evento de auditoría son transacciones separadas; para producción conviene unificar ambas y enviar eventos a un almacenamiento independiente. Deben definirse respaldos, restauración, conservación, MFA, cifrado del disco y monitoreo antes del uso clínico real.

## Herramientas solicitadas

```bash
python3 -m venv venv_seguridad
venv_seguridad/bin/python -m pip install -r requirements-security.txt
bash scripts/auditar.sh
```

| Revisión | Herramienta | Archivo de evidencia |
|---|---|---|
| SCA | pip-audit 2.10.1 | reportes/sca.json |
| SAST Python | Bandit 1.9.4 | reportes/bandit.json |
| SAST multi-regla | Semgrep CE 1.177.0, p/python y p/owasp-top-ten (Python) | reportes/semgrep.json |
| Funcionales / acceso | unittest | reportes/tests.log |
| DAST pasivo | OWASP ZAP 2.17.0 | exportación HTML/JSON en entorno local |
| DAST activo limitado | OWASP ZAP 2.17.0 | exportación HTML/JSON en base ficticia |
| Manual TLS/cabeceras | curl / OpenSSL | reportes/https_headers.txt y openssl.txt |
| Git | git grep / scripts Python | reportes/git_revision.txt |

El script no transforma fallos de instalación, red o configuración en “0 alertas”. Semgrep requiere acceso al registro de reglas y deja documentados errores/archivos omitidos. SCA revisa todas las dependencias runtime enumeradas; las herramientas van en un entorno separado. Bandit/Semgrep revisan el código Python de `app` y `run.py`; las plantillas Jinja se verifican mediante tests de renderizado y XSS. Una pasada adicional sobre HTML produjo avisos de parsing parcial de Jinja, conservados en la evidencia, y no se considera cobertura completa de plantillas. no equivalen a una auditoría del instalador, SO, proxy ni sistema completo.

Para pruebas manuales, con el servidor HTTPS funcionando, abre otra terminal:

```bash
bash scripts/pruebas_https.sh
venv/bin/python -m unittest discover -s tests -v
```

Revisa que curl valida el certificado, que OpenSSL verifica el nombre y que aparece TLS 1.2 o 1.3. Las peticiones sin sesión se redirigen a login. Prueba cada rol desde una ventana privada, accesos directos a /usuarios, /auditoria y /pacientes/ID, y verificación de 403 sin incluir HTML clínico en recepción.

## ZAP 2.17.0 — DAST pasivo

Descarga la versión indicada desde https://www.zaproxy.org/download/ y verifica la suma publicada. ZAP 2.17 necesita Java 17 o superior para la distribución Java. Ejecuta solo contra tu aplicación autorizada.

1. Configura un contexto para `https://172.24.189.179:8443/.*` y comprueba acceso a la IP de la VM.
2. Usa Manual Explore / navegador iniciado desde ZAP. Ese navegador utiliza el proxy y el certificado de ZAP para inspeccionar HTTPS. Configura la confianza del certificado del servidor local según las opciones de ZAP.
3. Inicia sesión y navega con cada rol: lista, ficha, usuarios y auditoría. Registra datos ficticios para que existan páginas clínicas.
4. Espera a que la cola de análisis pasivo llegue a cero. El análisis pasivo examina el tráfico observado; no demuestra cobertura de páginas que no navegaste.
5. Genera el reporte HTML/JSON y registra versión de ZAP, complementos, fecha, URLs y rol usado. Diferencia alertas confirmadas, falsos positivos y cobertura pendiente.

## ZAP — DAST activo limitado

Realiza este análisis sobre una **copia aislada con datos ficticios**, no la base de tu práctica. Puedes generar otra carpeta ejecutando una copia del actualizador en esa carpeta, creando su venv y certificados. Detén el servidor principal y usa el mismo puerto; no copies la base original. Crea usuarios de prueba.

1. En ZAP crea un contexto que incluya solo páginas GET de lectura (por ejemplo `/` y `/pacientes/1`) observadas tras iniciar sesión con un usuario profesional de prueba.
2. Excluye `/agenda/generar`, `/agenda/tipos.*`, `.*/reservar`, `.*/reprogramar`, `.*/cancelar`, `.*/documentos`, `.*/descargar`, `/admisiones/nueva`, `/admisiones/importar`, `.*/editar`, `.*/atender`, `/login`, `/logout`, `/password`, `/usuarios.*`, `/profesionales`, `/pacientes/nuevo`, `.*/eliminar` y `.*/atenciones` del análisis activo. No uses POST de creación o cambio de estado como objetivos.
3. Configura la autenticación y la gestión de sesión del contexto: formulario login, campos username/password, token CSRF `csrf` y usuario de prueba. Comprueba que la sesión permanece autenticada y que el indicador de logout no aparece; si el escáner termina en login, el resultado no cubre páginas protegidas.
4. Selecciona expresamente las solicitudes GET permitidas, evita recorrido automático fuera de contexto, usa una política de intensidad baja y un hilo. Mantén fuera del alcance cualquier otro servicio.
5. Exporta el reporte y registra contexto, URLs, política, usuario, hora y hallazgos. La auditoría puede crecer y se recomienda limpiar la copia completa al finalizar.

El DAST activo intenta ataques; su cobertura es limitada por diseño. No cambia la necesidad de validar permisos e identidades con las pruebas automatizadas.

## Git

No agregues SQLite, certificados privados, claves, entornos ni respaldos. `.gitignore` no retira archivos que ya estén registrados. El script revisa nombres sin mostrar secretos. Dentro de tu repositorio puedes usar:

```bash
git grep -n -E 'debug[[:space:]]*=[[:space:]]*True|shell[[:space:]]*=[[:space:]]*True|eval\(|exec\(' -- app run.py
venv/bin/python scripts/revisar_git.py
```

Un código de salida 1 de git grep significa que no encontró coincidencias; errores de repositorio no deben tratarse como revisión aprobada. El script solo revisa el árbol actual, no todo el historial. Si publicaste una clave, debes rotarla y revisar el historial.

## Fuentes oficiales
- OWASP Top 10 2025: https://top10.owasp.org/2025/es/
- Seguridad Flask: https://flask.palletsprojects.com/en/stable/web-security/
- Hashes Werkzeug: https://werkzeug.palletsprojects.com/en/stable/utils/
- ZAP 2.17.0: https://www.zaproxy.org/docs/desktop/releases/2.17.0/
- Semgrep: https://docs.semgrep.dev/running-rules
