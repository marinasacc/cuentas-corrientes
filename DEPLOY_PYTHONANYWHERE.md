# Como publicar la app en internet (PythonAnywhere)

Guia paso a paso para que la app quede disponible desde cualquier lado, gratis.

---

## PARTE 1 — Crear cuenta en PythonAnywhere

1. Abri https://www.pythonanywhere.com/registration/register/beginner/
2. Elegi un **username** corto (sera parte de tu URL, ej: `tutextil` → `tutextil.pythonanywhere.com`)
3. Usa tu email y crea una contrasena
4. Confirma el email
5. Ya tenes cuenta gratuita

---

## PARTE 2 — Subir el codigo

### Opcion A: con consola de PythonAnywhere (mas simple)

1. Una vez logueada, hace click en **"Consoles"** arriba a la derecha
2. Click en **"Bash"** para abrir una terminal
3. En la consola, escribi:

   ```bash
   cd ~
   mkdir -p cuentas_corrientes
   cd cuentas_corrientes
   ```

4. Ahora vas a subir cada archivo del proyecto. En el menu superior, click en **"Files"**.
5. Navega a `/home/tu_usuario/cuentas_corrientes/`
6. Subi todos los archivos del proyecto, manteniendo la estructura de carpetas:
   - `app.py`
   - `backup_drive.py`
   - `wsgi.py`
   - `requirements.txt`
   - Carpeta `templates/` (con los 5 archivos .html)
   - Carpeta `static/` (con `css/styles.css` y los 3 .js)

   No subas: `database/`, `uploads/`, `exports/`, `smtp_config.json`, `login_config.json`, `.git/`, `__pycache__/`

7. Volve a la consola Bash y ejecuta:

   ```bash
   cd ~/cuentas_corrientes
   pip3.10 install --user -r requirements.txt
   ```

   Esto va a tardar unos minutos.

---

## PARTE 3 — Configurar la app web

1. En el menu superior, click en **"Web"**
2. Click en **"Add a new web app"**
3. Elegi:
   - **Manual configuration** (NO Flask, importante)
   - **Python 3.10**
4. Se va a crear la web app. Ahora vas a configurar el archivo WSGI.
5. En la pagina "Web" busca la seccion **"Code"**, y hace click en el link del archivo WSGI (algo como `/var/www/tutextil_pythonanywhere_com_wsgi.py`)
6. Borra TODO el contenido del archivo y reemplazalo con esto (cambiando `tutextil` por tu usuario):

   ```python
   import sys
   import os

   project_home = '/home/TU_USUARIO/cuentas_corrientes'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   os.chdir(project_home)

   from app import app as application
   ```

7. Click **"Save"** arriba a la derecha
8. Volve a la pagina **"Web"** y click el boton verde **"Reload"**

---

## PARTE 4 — Subir archivos de configuracion

En **"Files"**, dentro de `~/cuentas_corrientes/`, crea los archivos:

### `smtp_config.json`

```json
{
  "servidor": "smtp.gmail.com",
  "puerto": 587,
  "usuario": "enviadorreuniones@gmail.com",
  "password": "TU_APP_PASSWORD_AQUI"
}
```

(El mismo que tenes en local)

### `google_credentials.json`

Copia el contenido del archivo `C:\Users\maru\Documents\claudio\data\google_credentials.json`

### `drive_config.json`

Primero:
1. Andate a tu Google Drive
2. Crea una carpeta nueva llamada **"Backups Cuentas Corrientes"**
3. Hace click derecho en la carpeta → **Compartir**
4. Agrega como Editor el email: `claudio@claudio-491623.iam.gserviceaccount.com`
5. Click en la carpeta para abrirla. En la URL veras algo como:
   `https://drive.google.com/drive/folders/1AbCd2EfGh3IjKlM4NoP_xyz`
   Copia esa ultima parte (`1AbCd2EfGh3IjKlM4NoP_xyz`) — es el folder_id

Ahora crea el archivo `drive_config.json` con:

```json
{
  "folder_id": "PEGAR_AQUI_EL_FOLDER_ID"
}
```

---

## PARTE 5 — Probar la app

1. Andate a `https://tu_usuario.pythonanywhere.com`
2. Te va a mostrar la pantalla de **Configuracion inicial** para crear usuario y contrasena
3. Crea el usuario que vas a compartir con el equipo
4. Hace login
5. Carga el primer Excel y listo

---

## PARTE 6 — Configurar backup automatico semanal

1. En el menu superior, click en **"Tasks"**
2. Crea una **Scheduled task**:
   - **Time**: 03:00 UTC (~ 00:00 hora Argentina) los Lunes
   - **Command**:
     ```
     python3.10 /home/TU_USUARIO/cuentas_corrientes/backup_drive.py
     ```
3. Click "Create"

Esto va a copiar la base a tu Drive todos los lunes a la madrugada.

Tambien podes correrlo manualmente cuando quieras desde la consola:

```bash
cd ~/cuentas_corrientes
python3.10 backup_drive.py
```

---

## Listo!

Tu app esta corriendo en `https://tu_usuario.pythonanywhere.com`.

### Para actualizar el codigo en el futuro

1. Subi los archivos modificados via **"Files"**
2. Andate a **"Web"** y click en **"Reload"**

### Si algo no funciona

- Revisa los logs en la pagina **"Web"** → seccion **"Log files"** → "Error log"
- O en la consola Bash:
  ```bash
  tail -50 /var/log/tu_usuario.pythonanywhere.com.error.log
  ```
