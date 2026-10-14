import ssl
from pathlib import Path
from app import create_app

app = create_app()

if __name__ == '__main__':
    base = Path(__file__).resolve().parent
    cert = base / 'certs' / 'cert.pem'
    key = base / 'certs' / 'key.pem'
    if not cert.is_file() or not key.is_file():
        raise SystemExit('Faltan certificados. Ejecuta: bash scripts/crear_certificado.sh')
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    contexto.load_cert_chain(str(cert),str(key))
    app.run(host=app.config['BIND_HOST'],port=8443,debug=False,ssl_context=contexto)
