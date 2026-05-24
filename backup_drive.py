"""
Backup automatico de la base de datos a Google Drive.
Se ejecuta semanalmente desde PythonAnywhere (tarea programada).

Requisitos:
1. google_credentials.json (cuenta de servicio) en la carpeta del proyecto
2. drive_config.json con el ID de la carpeta destino en Drive
3. Compartir esa carpeta en Drive con el email de la cuenta de servicio (Editor)
"""

import os
import json
import shutil
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'cuentas.db')
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'google_credentials.json')
DRIVE_CONFIG_PATH = os.path.join(BASE_DIR, 'drive_config.json')
BACKUPS_LOCAL_DIR = os.path.join(BASE_DIR, 'backups')

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def hacer_backup():
    """Hace backup local y sube a Drive."""
    if not os.path.exists(DB_PATH):
        print('ERROR: No existe la base de datos en', DB_PATH)
        return False

    # Backup local primero (por si falla Drive)
    os.makedirs(BACKUPS_LOCAL_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'cuentas_{timestamp}.db'
    backup_path = os.path.join(BACKUPS_LOCAL_DIR, backup_name)

    shutil.copy2(DB_PATH, backup_path)
    print(f'[OK] Backup local creado: {backup_path}')

    # Limpiar backups locales viejos (dejar solo los ultimos 10)
    limpiar_backups_locales()

    # Subir a Drive
    if not os.path.exists(CREDENTIALS_PATH):
        print('AVISO: No existe google_credentials.json. No se sube a Drive.')
        return True

    if not os.path.exists(DRIVE_CONFIG_PATH):
        print('AVISO: No existe drive_config.json. No se sube a Drive.')
        print('       Crear con: {"folder_id": "ID_de_la_carpeta_en_Drive"}')
        return True

    try:
        with open(DRIVE_CONFIG_PATH, 'r') as f:
            drive_config = json.load(f)
        folder_id = drive_config.get('folder_id', '')

        if not folder_id:
            print('AVISO: folder_id vacio en drive_config.json')
            return True

        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': backup_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(backup_path, mimetype='application/x-sqlite3')

        result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()

        print(f'[OK] Subido a Drive: {result.get("name")}')
        print(f'     Link: {result.get("webViewLink")}')

        # Limpiar backups viejos en Drive (dejar solo los ultimos 12 = 3 meses)
        limpiar_backups_drive(service, folder_id)

        return True

    except Exception as e:
        print(f'[ERROR] al subir a Drive: {e}')
        return False


def limpiar_backups_locales(maximo=10):
    """Eliminar backups locales viejos."""
    if not os.path.exists(BACKUPS_LOCAL_DIR):
        return
    archivos = sorted([
        os.path.join(BACKUPS_LOCAL_DIR, f)
        for f in os.listdir(BACKUPS_LOCAL_DIR)
        if f.endswith('.db')
    ], key=os.path.getmtime, reverse=True)

    for archivo in archivos[maximo:]:
        os.remove(archivo)
        print(f'[OK] Eliminado backup local viejo: {os.path.basename(archivo)}')


def limpiar_backups_drive(service, folder_id, maximo=12):
    """Eliminar backups viejos de Drive, dejando solo los ultimos N."""
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and name contains 'cuentas_' and trashed = false",
            orderBy='createdTime desc',
            fields='files(id, name, createdTime)'
        ).execute()

        archivos = results.get('files', [])
        for archivo in archivos[maximo:]:
            service.files().delete(fileId=archivo['id']).execute()
            print(f'[OK] Eliminado backup viejo en Drive: {archivo["name"]}')
    except Exception as e:
        print(f'[AVISO] No se pudieron limpiar backups viejos en Drive: {e}')


if __name__ == '__main__':
    print('=' * 50)
    print(f'BACKUP - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)
    exito = hacer_backup()
    print('=' * 50)
    print('Backup OK' if exito else 'Backup con errores')
