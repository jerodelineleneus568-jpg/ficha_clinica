#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p reportes
umask 077
curl --fail --silent --show-error --cacert certs/cert.pem -D reportes/https_headers.txt -o /dev/null https://172.24.189.179:8443/login
curl --silent --show-error --cacert certs/cert.pem -D reportes/acceso_sin_sesion.txt -o /dev/null https://172.24.189.179:8443/
openssl s_client -connect 172.24.189.179:8443 -servername 172.24.189.179 -CAfile certs/cert.pem -verify_ip 172.24.189.179 -verify_return_error </dev/null > reportes/openssl.txt 2>&1
openssl s_client -connect 172.24.189.179:8443 -servername 172.24.189.179 -tls1_2 -CAfile certs/cert.pem -verify_return_error </dev/null > reportes/tls12.txt 2>&1
printf 'Revisa certificado, cabeceras y redirección a login en reportes/.\n'
