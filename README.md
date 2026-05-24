# Cuentas Corrientes - Tu Textil

Aplicacion web para gestionar las cuentas corrientes (cobranzas) de clientes de Tu Textil / Tucuman Textil.

**App en produccion**: https://tutextil.pythonanywhere.com
**Repositorio**: https://github.com/marinasacc/cuentas-corrientes

---

## Funcionalidades

### Pantalla principal
- Grilla con todos los clientes y sus saldos por antiguedad
- Buscador por codigo o nombre
- Filtros por antiguedad de saldo (0-30, 31-60, 61-90, +91 dias)
- Filtros clickeables por estado de contacto (Contactados / Sin contactar)
- Indicador de checkbox "contactado" (se marca si hubo contacto desde la ultima carga de Excel)
- Columna "Ultimo movimiento" — fecha del ultimo cambio detectado en los saldos
- Header de la tabla fijo al scrollear
- Botones flotantes: cargar Excel, exportar contactos, historial de cargas, backup manual

### Detalle del cliente
- Datos editables: email, telefono, notas
- Tabla de saldos por antiguedad
- Historial de contactos ordenado por fecha
  - Cada contacto registra: fecha, persona, respuesta, comentario, proxima fecha
  - Borrado logico (queda visible tachado en rojo con badge BORRADO)
- Boton para nuevo contacto (modal)
- Boton para enviar recordatorio via Google Calendar (modal)

### Carga de Excel (proveniente de Magus)
- Primera carga: inicializa la base
- Cargas posteriores: detecta cambios (pagos totales, cambios de saldo, clientes nuevos)
- Pantalla de actualizaciones con las diferencias

### Recordatorios via Google Calendar
- Modal con titulo, descripcion, fecha
- Combo con los emails del equipo (persistentes en BD)
- Posibilidad de agregar nuevos contactos al equipo (boton +)
- Envia invitacion .ics por SMTP a los seleccionados

### Backup automatico
- Cada 24hs, al usar la app, se hace backup automatico en segundo plano
- Backup local (carpeta `backups/`) + subida a Google Drive
- Indicador en la navbar muestra "Backup hace Xh"
- Boton flotante para forzar backup manual
- Mantiene los ultimos 10 backups locales y 12 en Drive

### Login
- Una sola cuenta compartida por el equipo
- En la primera ejecucion, pantalla de setup para crear usuario y contrasena
- Hash de contrasena con werkzeug, sesiones firmadas con secret key persistente
- Sesion persiste 30 dias si se marca "Recordarme"

---

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.10 + Flask |
| Base de datos | SQLite |
| Frontend | HTML + Bootstrap 5 + JS vanilla |
| Email/Calendar | SMTP (Gmail) + archivos ICS |
| Autenticacion | Sesiones de Flask + werkzeug |
| Backup | Google Drive API (OAuth) |
| Hosting | PythonAnywhere (plan gratuito) |

---

## Estructura del proyecto

```
cuentas_corrientes/
├── app.py                      # Servidor Flask + endpoints API
├── backup_drive.py             # Script de backup a Google Drive (OAuth)
├── setup_oauth.py              # Script LOCAL para generar drive_token.json
├── wsgi.py                     # Entry point para PythonAnywhere
├── iniciar.bat                 # Lanzador para Windows (doble click)
├── requirements.txt            # Dependencias Python
├── README.md                   # Este archivo
├── CLAUDE.md                   # Contexto para Claude
├── DEPLOY_PYTHONANYWHERE.md    # Guia de deployment
├── .gitignore
├── templates/
│   ├── login.html
│   ├── setup.html
│   ├── principal.html
│   ├── detalle_cliente.html
│   └── actualizaciones.html
├── static/
│   ├── css/styles.css
│   └── js/
│       ├── principal.js
│       ├── detalle.js
│       └── actualizaciones.js
├── database/                   # (.gitignored)
│   └── cuentas.db              # SQLite
├── uploads/                    # (.gitignored) Excels cargados
├── exports/                    # (.gitignored) Excels exportados
├── backups/                    # (.gitignored) Backups locales
├── smtp_config.json            # (.gitignored) Credenciales SMTP
├── login_config.json           # (.gitignored) Hash de password + secret key
├── oauth_client_secret.json    # (.gitignored) Credenciales OAuth de Google
├── drive_token.json            # (.gitignored) Token OAuth generado
├── drive_config.json           # (.gitignored) ID de carpeta de Drive
├── google_credentials.json     # (.gitignored) Cuenta de servicio (legacy, ya no se usa)
└── backup_status.json          # (.gitignored) Timestamp del ultimo backup
```

---

## Archivos sensibles (NO se commitean)

Estos archivos contienen credenciales o datos privados. **No subirlos a GitHub.**

| Archivo | Contenido |
|---|---|
| `smtp_config.json` | App password de Gmail (cuenta `enviadorreuniones@gmail.com`) |
| `login_config.json` | Hash de contrasena de la app + secret key de Flask |
| `oauth_client_secret.json` | OAuth client ID y secret de Google Cloud |
| `drive_token.json` | Token de OAuth generado tras autorizar acceso a Drive |
| `drive_config.json` | ID de la carpeta de Drive donde van los backups |
| `database/cuentas.db` | Base de datos con todos los datos de clientes |
| `uploads/`, `exports/`, `backups/` | Excels y archivos generados |

---

## Setup desde cero (en una PC nueva)

### 1. Clonar el repo

```bash
git clone https://github.com/marinasacc/cuentas-corrientes.git
cd cuentas-corrientes
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar SMTP (envio de invitaciones de calendar)

Crear `smtp_config.json`:

```json
{
  "servidor": "smtp.gmail.com",
  "puerto": 587,
  "usuario": "enviadorreuniones@gmail.com",
  "password": "TU_APP_PASSWORD_DE_16_CARACTERES"
}
```

**Como obtener el app password**:
1. Entrar a https://myaccount.google.com/security con `enviadorreuniones@gmail.com`
2. Activar la verificacion en 2 pasos
3. Ir a https://myaccount.google.com/apppasswords
4. Crear una nueva con nombre "Cuentas Corrientes"
5. Copiar los 16 caracteres (sin espacios) al campo `password`

### 4. Configurar Google Drive (backups)

**Paso A: Crear credenciales OAuth en Google Cloud Console**

1. Entrar a https://console.cloud.google.com/apis/credentials
2. Seleccionar el proyecto (o crear uno nuevo)
3. Configurar OAuth consent screen (Externo, agregar `marina@tucumantextil.com.ar` como test user)
4. Crear credenciales: "OAuth 2.0 Client ID" tipo "Aplicacion de escritorio"
5. Descargar el JSON, renombrarlo a `oauth_client_secret.json` y ponerlo en la carpeta del proyecto

**Paso B: Habilitar Google Drive API**

1. Entrar a https://console.developers.google.com/apis/api/drive.googleapis.com/overview
2. Click en "Habilitar"

**Paso C: Crear carpeta en Drive y obtener su ID**

1. Crear carpeta en Google Drive donde van a vivir los backups
2. Abrir la carpeta, copiar el ID desde la URL (la parte despues de `/folders/`)
3. Crear `drive_config.json`:

```json
{
  "folder_id": "EL_ID_DE_LA_CARPETA"
}
```

**Paso D: Generar el token OAuth (en tu PC local, no en el server)**

```bash
python setup_oauth.py
```

Se abre el navegador, te logueas con `marina@tucumantextil.com.ar` y autorizas el acceso. Se genera `drive_token.json`.

### 5. Correr localmente

**Windows**: doble click en `iniciar.bat`

**Otra forma**:
```bash
python app.py
```

Abrir el navegador en http://localhost:5050

La primera vez te lleva a `/setup` para crear el usuario y contrasena de la app.

---

## Deployment a PythonAnywhere

Ver guia detallada en [`DEPLOY_PYTHONANYWHERE.md`](DEPLOY_PYTHONANYWHERE.md).

### Resumen

1. Crear cuenta gratuita en PythonAnywhere
2. Subir codigo (zip o git)
3. Instalar dependencias: `pip3.10 install --user -r requirements.txt`
4. Configurar archivo WSGI apuntando a `cuentas_corrientes/app.py`
5. Subir archivos sensibles: `smtp_config.json`, `oauth_client_secret.json`, `drive_token.json`, `drive_config.json`
6. Reload de la web app
7. Entrar a `https://tu_usuario.pythonanywhere.com` y crear el usuario

### Actualizar codigo en produccion

1. Subir los archivos modificados via Files
2. Andar a "Web" y click en "Reload"

### Backup automatico

PythonAnywhere gratis no permite scheduled tasks. La app hace backup automatico cada 24hs cuando alguien la usa (logica en `@app.before_request`).

Si no se usa la app por mas de 24hs, el backup se atrasa hasta que alguien entre. Para forzarlo, usar el boton de backup manual desde la UI.

---

## Excel de Magus

El archivo que se exporta de Magus (programa de gestion de la empresa) tiene este formato:

- **Sin fila de encabezado**, datos directo
- **~140 filas** con clientes
- Filas finales: "TOTAL" en pesos y "TOTAL" en U$S
- Solo procesamos clientes en pesos (columna D == `"$"`)
- Ignoramos la fila de U$S y los totales

### Mapeo de columnas

| Columna Excel | Indice | Contenido |
|---|---|---|
| A | 0 | Codigo del cliente (clave primaria) |
| B | 1 | Nombre del cliente |
| C | 2 | (vacia, ignorada) |
| D | 3 | Moneda (`$` o `U$S`) — filtramos por `$` |
| E | 4 | (otra de moneda, ignorada) |
| F | 5 | Saldo +91 dias |
| G | 6 | Saldo 61-90 dias |
| H | 7 | (vacia, ignorada) |
| I | 8 | Saldo 31-60 dias |
| J | 9 | Saldo 0-30 dias |
| K | 10 | (ignorada) |
| L | 11 | (vacia, ignorada) |
| M | 12 | Saldo total |

---

## Personas y emails

### Equipo (para registrar quien contacto al cliente)

Hardcodeados en `app.py` (variable `EQUIPO`):
Marina, Alberto, Juan Fanti, Romina, Fabiana, Sergio, Otro

### Emails para recordatorios de calendar

Se cargan en la BD la primera vez (variable `EMAILS_INICIALES` en `app.py`). Se pueden agregar/quitar desde la UI:

- fabiana.galaratti@gmail.com
- romizub@gmail.com
- sergio@tucumantextil.com
- albertojota2020@gmail.com

### Cuentas de Google involucradas

| Cuenta | Para que se usa |
|---|---|
| `marina@tucumantextil.com.ar` | Cuenta principal. Dueña de los backups en Drive. Autoriza el OAuth |
| `enviadorreuniones@gmail.com` | Solo para enviar emails con invitaciones de calendar (SMTP) |
| `claudio@claudio-491623.iam.gserviceaccount.com` | Cuenta de servicio (legacy). Ya no se usa para Drive porque no tiene cuota |

---

## Workflow comun

### Para usar la app

1. Entrar a https://tutextil.pythonanywhere.com
2. Login
3. Si es la primera vez: cargar el Excel de Magus
4. Revisar la grilla, filtrar por antiguedad o por estado de contacto
5. Click en un cliente para ver el detalle
6. Cargar nuevo contacto / enviar recordatorio / editar datos

### Para actualizar saldos (cuando exportas nuevo Excel de Magus)

1. Pantalla principal -> Boton flotante de Excel (icono nube hacia arriba)
2. Seleccionar el nuevo archivo
3. La app compara con la version anterior y muestra los cambios
4. Confirmar para actualizar la base

### Para hacer un cambio en el codigo

1. Editar localmente en `C:\Users\maru\Documents\claudio\cuentas_corrientes\`
2. Probar local: `python app.py` (o doble click en `iniciar.bat`)
3. Commit y push a GitHub
4. Subir los archivos modificados a PythonAnywhere via Files
5. En PythonAnywhere -> Web -> click "Reload"

---

## Troubleshooting

### El backup no anda

1. Verificar que existan: `drive_token.json`, `drive_config.json`, `oauth_client_secret.json`
2. Si el token expiro y no se puede refrescar (raro, pero pasa si la cuenta cambio password), regenerar con `python setup_oauth.py` y subir el nuevo `drive_token.json` a PythonAnywhere
3. Revisar la consola de PythonAnywhere: `cd ~/cuentas_corrientes && python3.10 backup_drive.py`

### Los emails de calendar no llegan

1. Verificar `smtp_config.json` - la `password` debe ser el app password (16 chars sin espacios)
2. Probar reenviando desde la UI y revisar logs en PythonAnywhere ("Web" -> "Log files" -> Error log)

### Error 500 en alguna pantalla

Revisar el Error log de PythonAnywhere:
- En el menu "Web" -> seccion "Log files"
- O en consola: `tail -50 /var/log/tutextil.pythonanywhere.com.error.log`

### Quiero restaurar un backup

1. Bajar el archivo `.db` desde Drive ("Backups Cuentas Corrientes")
2. Subirlo a PythonAnywhere como `database/cuentas.db` (sobreescribir)
3. Reload de la web app
