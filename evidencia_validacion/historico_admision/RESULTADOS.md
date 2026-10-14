# Validación de la versión de admisión

13 de octubre de 2026, entorno local de construcción, datos ficticios. No es la validación del servidor de la usuaria.

- 14 pruebas aprobadas: seguridad previa, migración de cuentas existentes, CRUD, versiones obsoletas, Excel válido, lote inválido sin importación parcial, fórmulas, aislamiento del portal de pacientes, dos funcionarios para un paciente y guardado único del historial.
- pip-audit 2.10.1: 10 dependencias runtime; 0 vulnerabilidades conocidas reportadas.
- Bandit 1.9.4: app y run.py, 0 hallazgos, 0 errores.
- Semgrep CE 1.177.0: p/python y p/owasp-top-ten, 156 reglas, 16 archivos Python, 0 hallazgos, 0 errores. Las plantillas no forman parte del SAST Python; se renderizaron en los tests.
- Revisión Git del árbol distribuido ensayada en una copia temporal, 0 señales. El historial y el repositorio de la usuaria quedan pendientes.
- ZAP pasivo y activo limitado: pendiente en el entorno de la usuaria. Las rutas nuevas amplían la superficie y necesitan nuevo DAST.
- TLS: los resultados anteriores se conservan en historico_seguridad y no validan el certificado, IP o servidor actual. Ejecuta scripts/pruebas_https.sh en tu Ubuntu tras iniciar la aplicación.

No equivale a cumplimiento completo OWASP ni a certificación clínica. Repite las herramientas para el despliegue real y documenta fecha, versiones, alcance y hallazgos. No se distribuyen certificados privados, SQLite ni secretos de usuarios.
