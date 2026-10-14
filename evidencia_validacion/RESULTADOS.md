# Validación de agenda, citas y documentos

14 de octubre de 2026, entorno de construcción con datos ficticios. No corresponde al servidor de la usuaria.

- 22 pruebas aprobadas. Incluyen generación por intervalos, pausas, rechazo de cruces, capacidad grupal, reserva concurrente sin sobreventa, reprogramación, cancelación que libera cupo, CRUD, tipos, vinculación con admisión, atención e historial y permisos de adjuntos.
- pip-audit 2.10.1: 10 dependencias runtime, 0 vulnerabilidades conocidas reportadas.
- Bandit 1.9.4: código Python app y run.py, 0 hallazgos, 0 errores.
- Semgrep CE 1.177.0: p/python y p/owasp-top-ten, 156 reglas, 21 archivos Python, 0 hallazgos, 0 errores. No cubre las plantillas HTML; sus páginas principales se renderizaron en los tests.
- El actualizador se verifica adicionalmente en una copia con IP distinta, base existente y certificados para comprobar preservación. No cambia automáticamente el SAN del certificado.
- Los resultados de versiones anteriores están en historico_seguridad e historico_admision. No sustituyen el DAST ni la revisión del repositorio actual.
- ZAP pasivo/activo, manual TLS y Git del servidor de la usuaria: pendientes de repetir con las rutas nuevas.

La comprobación de firma y tamaño de adjuntos no es un análisis antivirus ni validación estructural completa. Se descargan como archivos adjuntos autenticados, sin ejecutarse ni mostrarse embebidos en el servidor. Sigue pendiente el análisis antimalware y el diseño institucional de retención/cifrado de disco.

No equivale a una certificación OWASP o clínica. Repite las revisiones en el despliegue real y documenta versión, fecha y alcance.
