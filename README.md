# Cuentas Corrientes - Tu Textil

Aplicacion web para gestionar las cuentas corrientes (cobranzas) de clientes de Tu Textil / Tucuman Textil.

## Funcionalidades

- 📊 **Pantalla principal**: grilla con todos los clientes, busqueda, filtros por antiguedad de saldo (0-30, 31-60, 61-90, +91 dias)
- 👤 **Detalle del cliente**: datos editables (email, telefono, notas), saldos y historial de contactos
- 📝 **Historial de contacto**: registrar cada vez que se contacta al cliente, con respuesta y proxima fecha
- 🔔 **Recordatorios por Calendar**: enviar invitaciones automaticas via email (.ics) a los miembros del equipo
- 📥 **Carga de Excel**: importar saldos desde Magus, comparar con la version anterior y mostrar cambios
- 📤 **Exportar contactos**: descargar Excel con los datos de contacto de todos los clientes
- 🔐 **Login**: cuenta compartida para todo el equipo
- ☁️ **Backup automatico**: backup semanal de la base de datos a Google Drive

## Tecnologia

- **Backend**: Python 3.10 + Flask
- **Base de datos**: SQLite
- **Frontend**: HTML + Bootstrap 5 + JavaScript vanilla
- **Email**: SMTP (Gmail) con archivos ICS para invitaciones de calendar
- **Hosting**: PythonAnywhere (plan gratuito)

## Estructura

```
cuentas_corrientes/
├── app.py                      # Servidor Flask + endpoints API
├── backup_drive.py             # Script de backup a Google Drive
├── wsgi.py                     # Entry point para deployment
├── requirements.txt            # Dependencias Python
├── iniciar.bat                 # Script para correr en local (Windows)
├── templates/                  # Templates HTML
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
└── DEPLOY_PYTHONANYWHERE.md    # Guia de deployment
```

## Archivos sensibles (NO commiteados)

Los siguientes archivos contienen credenciales y NO se suben al repositorio:

- `smtp_config.json` — password de Gmail para enviar invitaciones
- `login_config.json` — hash de password de la app + secret key
- `google_credentials.json` — credenciales de cuenta de servicio Google
- `drive_config.json` — ID de la carpeta de Drive donde se guardan backups
- `database/` — base de datos SQLite
- `uploads/` — Excels cargados
- `exports/` — Excels exportados
- `backups/` — backups locales de la DB

## Como correr en local

```bash
pip install -r requirements.txt
python app.py
```

Abrir el navegador en http://localhost:5050

En Windows: doble click en `iniciar.bat`

## Como deployear

Ver `DEPLOY_PYTHONANYWHERE.md` para la guia completa de deployment.
