import ipaddress
import json
import os
from pathlib import Path

def configuracion_red(instance):
    p=Path(instance)/'network.json'
    saved=json.loads(p.read_text()) if p.is_file() else {}
    host=os.environ.get('FICHA_HOST') or saved.get('host','172.24.189.179')
    if host!='localhost':
        direccion=ipaddress.ip_address(host)
        if direccion.is_unspecified:
            raise ValueError('Configura una IP concreta de Ubuntu o localhost.')
    hosts=['localhost','127.0.0.1','[::1]']
    if host!='localhost':
        hosts.append(host)
    for v in saved.get('trusted_hosts',[]):
        if v in hosts:
            continue
        try:
            ipaddress.ip_address(v.strip('[]'))
        except ValueError:
            continue
        hosts.append(v)
    return host,hosts
