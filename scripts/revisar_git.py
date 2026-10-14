"""Revisa archivos de Git sin imprimir sus contenidos o secretos."""
import re
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
result=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=False)
if result.returncode:
    raise SystemExit('No hay un repositorio Git: revisión pendiente. Inicializa tu repositorio antes de entregar esta evidencia.')
files=[p for p in result.stdout.decode().split('\0') if p]
if not files:
    raise SystemExit('No hay archivos registrados en Git: revisión pendiente.')
issues=[]
for name in files:
    parts=Path(name).parts
    if any(part in ('instance','certs','venv','venv_seguridad') or (part.startswith('respaldo_') or part.startswith('certs_respaldo_')) for part in parts) or name.endswith(('.sqlite','.pem','.key','.env')):
        issues.append((name,'Archivo privado o entorno registrado en Git'))
        continue
    if not name.endswith('.py') or not (name.startswith('app/') or name=='run.py'):
        continue
    content=(root/name).read_text(encoding='utf-8')
    for pattern,reason in [(r'\bdebug\s*=\s*True','Debug activo'),(r'\bshell\s*=\s*True','Shell activo'),(r'\b(?:eval|exec)\s*\(','Evaluación dinámica'),(r'\b(?:password|SECRET_KEY|api_key)\s*=\s*[\'"][^\'"]+[\'"]','Posible secreto literal')]:
        if re.search(pattern,content):
            issues.append((name,reason))
for name,reason in issues:
    print(name+': '+reason)
print(f'Archivos Git revisados: {len(files)}; señales: {len(issues)}. Revisión de árbol actual; el historial requiere revisión adicional.')
raise SystemExit(1 if issues else 0)
