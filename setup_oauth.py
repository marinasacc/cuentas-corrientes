"""
Setup unico de OAuth para subir backups a Google Drive.

Correr en tu PC (no en PythonAnywhere). Abre el navegador para que
autorices el acceso. Guarda un token que se puede usar para siempre.

Pasos:
1. Generar oauth_client_secret.json en Google Cloud Console
2. Ponerlo en esta carpeta (cuentas_corrientes/)
3. Correr: python setup_oauth.py
4. Loguearte con marina@tucumantextil.com.ar y autorizar
5. Subir el drive_token.json generado a PythonAnywhere
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET = os.path.join(BASE_DIR, 'oauth_client_secret.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'drive_token.json')

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def main():
    if not os.path.exists(CLIENT_SECRET):
        print('ERROR: No se encuentra oauth_client_secret.json')
        print()
        print('Pasos para obtenerlo:')
        print('1. Ir a: https://console.cloud.google.com/apis/credentials')
        print('2. Crear credenciales -> ID de cliente OAuth 2.0')
        print('3. Tipo: Aplicacion de escritorio')
        print('4. Descargar el JSON')
        print('5. Renombrarlo a "oauth_client_secret.json"')
        print(f'6. Ponerlo en: {BASE_DIR}')
        return

    print('Abriendo navegador para autorizar...')
    print('Logueate con marina@tucumantextil.com.ar')
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(
        port=0,
        success_message='Autorizacion exitosa! Ya podes cerrar esta ventana.',
        open_browser=True
    )

    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

    print('=' * 50)
    print(f'[OK] Token guardado en: {TOKEN_FILE}')
    print('=' * 50)
    print()
    print('Proximo paso:')
    print('  Subi el archivo drive_token.json a PythonAnywhere')
    print('  (carpeta cuentas_corrientes/)')


if __name__ == '__main__':
    main()
