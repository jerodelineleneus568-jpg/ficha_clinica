# Validación de esta distribución

Ejecutada el 13 de octubre de 2026 en un entorno local de construcción con datos ficticios. No corresponde al servidor de la usuaria.

| Revisión | Resultado |
|---|---|
| Tests unittest | 6 pruebas aprobadas: roles, identidad clínica, migración, XSS, CSRF, HTTPS, Host, bloqueo, sesiones, revocación, conservación de auditoría |
| pip-audit 2.10.1 | 7 dependencias runtime, 0 vulnerabilidades conocidas reportadas |
| Bandit 1.9.4 | 0 hallazgos y 0 errores; app y run.py |
| Semgrep CE 1.177.0 | 156 reglas ejecutadas, 11 archivos Python, 0 hallazgos, 0 errores; p/python y p/owasp-top-ten |
| Semgrep HTML adicional | 0 hallazgos, 4 avisos de parsing parcial de Jinja: cobertura incompleta de HTML |
| curl y OpenSSL | Certificado y hostname verificados; TLS 1.3 y conexión TLS 1.2; cabeceras presentes; sin sesión redirige a login |
| Git / script Python | Ensayado en repositorio temporal del código distribuido; no sustituye revisión del repositorio e historial de la usuaria |
| ZAP pasivo y activo | Pendiente: ZAP/Docker no disponibles en este entorno; guía en SEGURIDAD.md |

No se descartaron avisos HTML para presentar cobertura total; se conserva la pasada parcial separadamente. Las reglas del registro de Semgrep y las bases SCA pueden cambiar. Repite las revisiones y conserva versiones, fecha y alcance. Los certificados y cookies no se distribuyen como credenciales. No existe una garantía de ausencia de vulnerabilidades.
