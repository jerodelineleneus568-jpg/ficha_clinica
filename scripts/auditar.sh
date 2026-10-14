#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p reportes
umask 077
if [[ ! -x venv_seguridad/bin/pip-audit ]]; then
    echo "Primero crea venv_seguridad e instala requirements-security.txt."
    exit 2
fi
venv_seguridad/bin/pip-audit --version > reportes/versiones.txt
venv_seguridad/bin/bandit --version >> reportes/versiones.txt
venv_seguridad/bin/semgrep --version >> reportes/versiones.txt
venv_seguridad/bin/pip-audit -r requirements.txt --strict --disable-pip --no-deps -f json -o reportes/sca.json > reportes/sca.log 2>&1
sca=$?
venv_seguridad/bin/bandit -r app run.py -f json -o reportes/bandit.json > reportes/bandit.log 2>&1
bandit=$?
venv_seguridad/bin/semgrep scan --config p/python --config p/owasp-top-ten --include '*.py' --metrics off --disable-version-check --json --output reportes/semgrep.json app run.py > reportes/semgrep.log 2>&1
semgrep=$?
if [[ "$semgrep" -eq 0 ]]; then
    venv_seguridad/bin/python -c "import json; from pathlib import Path; d=json.loads(Path('reportes/semgrep.json').read_text()); raise SystemExit(1 if d.get('errors') else 0)"
    semgrep=$?
fi
venv/bin/python -m unittest discover -s tests -v > reportes/tests.log 2>&1
tests=$?
venv/bin/python scripts/revisar_git.py > reportes/git_revision.txt 2>&1
git_estado=$?
printf 'SCA=%s Bandit=%s Semgrep=%s Tests=%s Git=%s\n' "$sca" "$bandit" "$semgrep" "$tests" "$git_estado" | tee reportes/estado.txt
if [[ "$sca" -ne 0 || "$bandit" -ne 0 || "$semgrep" -ne 0 || "$tests" -ne 0 || "$git_estado" -ne 0 ]]; then
    echo "Hay hallazgos o revisiones incompletas. Revisa cada reporte; no equivale a 0 alertas."
    exit 1
fi
