"""Prueba opcional de interfaz. Requiere playwright y Chromium; usa datos temporales."""
import sys
import tempfile
import threading
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_clinica import ClinicaTest
from app.models.database import get_db
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

def main():
    fixture=ClinicaTest();fixture.setUp();fixture.paciente()
    server=None
    try:
        # Isolated HTTP fixture; production retains required HTTPS and secure cookies.
        fixture.app.config.update(REQUIRE_HTTPS=False,SESSION_COOKIE_SECURE=False,SESSION_COOKIE_NAME='ui-test',TRUSTED_HOSTS=['localhost','127.0.0.1'])
        with fixture.app.app_context():
            db=get_db()
            db.execute("INSERT INTO tipos_atencion(nombre,minutos,cupos) VALUES('Control UI',30,1)")
            db.commit()
        server=make_server('127.0.0.1',0,fixture.app)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://localhost:{server.server_port}'
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(url+'/login');page.locator('[name=username]').fill('admin');page.locator('[name=password]').fill('Frase de prueba larga')
            page.get_by_role('button',name='Mostrar',exact=True).click();assert page.locator('[name=password]').get_attribute('type')=='text'
            page.get_by_role('button',name='Ingresar a mi espacio').click();page.wait_for_url('**/inicio')
            assert page.locator('h1').inner_text()=='Hola, admin'
            page.screenshot(path='/tmp/ui_inicio_desktop.png',full_page=True)
            page.goto(url+'/agenda/generar');[checkbox.check() for checkbox in page.locator('[name=dias]').all()];page.locator('[name=tipo_id]').select_option(label='Control UI · 30 min / 1 cupo(s)')
            assert page.locator('[name=minutos]').input_value()=='30'
            assert '10 bloques' in page.locator('[data-agenda-preview]').inner_text()
            page.locator('[name=pausa_inicio]').fill('10:00');page.locator('[name=pausa_fin]').fill('11:00')
            assert '8 bloques' in page.locator('[data-agenda-preview]').inner_text()
            page.screenshot(path='/tmp/ui_agenda_desktop.png',full_page=True)
            page.goto(url+'/admisiones/nueva');page.locator('[name=paciente_id]').select_option('1');assert page.locator('[data-new-patient]').is_hidden()
            page.locator('[name=profesional_id]').select_option('1');assert page.locator('[name=especialidad]').input_value()=='Medicina'
            page.goto(url+'/usuarios');assert page.locator('[name=profesional_id]').is_hidden()
            page.locator('[name=rol]').select_option('profesional');assert page.locator('[name=profesional_id]').is_visible();assert page.locator('[name=paciente_id]').is_hidden()
            page.locator('[name=rol]').select_option('paciente');assert page.locator('[name=paciente_id]').is_visible();assert page.locator('[name=profesional_id]').is_hidden()
            page.set_viewport_size({'width':390,'height':844});page.goto(url+'/inicio')
            page.get_by_role('button',name='Menú').click();assert page.locator('#mobile-menu').is_visible()
            page.get_by_role('button',name='Menú').click();assert page.locator('#mobile-menu').is_hidden()
            for path in ['/inicio','/agenda','/admisiones','/agenda/generar','/usuarios','/']:
                page.goto(url+path)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),path
            page.goto(url+'/inicio');page.screenshot(path='/tmp/ui_inicio_movil.png',full_page=True)
            assert not errors,errors
            browser.close()
        print('OK: acceso e inicio, contraseña visible, duración automática, vista previa y pausa, paciente existente, especialidad, roles, menú móvil y 6 pantallas sin desborde horizontal; sin errores JavaScript.')
    finally:
        if server:server.shutdown()
        fixture.tearDown()

if __name__=='__main__':main()
