#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p certs
if [[ -e certs/cert.pem || -e certs/key.pem ]]; then
    echo "Ya existen certificados. No se reemplazan automáticamente."
    exit 0
fi
openssl req -x509 -newkey rsa:3072 -sha256 -noenc -days 90 \
    -keyout certs/key.pem -out certs/cert.pem \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1,IP:172.24.189.179" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign" \
    -addext "extendedKeyUsage=serverAuth"
chmod 600 certs/key.pem
echo "Certificado local generado. Confía solo en cert.pem; nunca distribuyas key.pem."
