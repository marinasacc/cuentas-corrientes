# CLAUDE.md - Cuentas Corrientes

Contexto para sesiones de Claude que trabajen sobre este proyecto.

## TL;DR

App web Flask para Maru (Tu Textil) que gestiona cobranzas. Cuando le pida hacer cambios, recordar:
- **Idioma: espanol** (UI y mensajes)
- **Simple por encima de elegante**: ella no programa, todo tiene que ser robusto y obvio
- **App en produccion**: https://tutextil.pythonanywhere.com — cualquier cambio hay que deployearlo manualmente subiendo archivos a PythonAnywhere
- **GitHub**: https://github.com/marinasacc/cuentas-corrientes (rama `main`)
- **Workflow de cambios**: editar local → probar local → commit + push → subir archivos modificados a PythonAnywhere → "Reload" en Web tab

## Que hace la app

Maru exporta de **Magus** (su sistema de gestion) un Excel con los saldos a cobrar. La app:
1. Importa el Excel (`.xls` formato viejo de Magus)
2. Muestra los clientes en una grilla con filtros
3. Permite registrar contactos con cada cliente (historial)
4. Envia recordatorios al equipo via Google Calendar (SMTP + ICS)
5. Compara cargas de Excel para detectar pagos y cambios
6. Hace backup automatico de la BD a Google Drive

## Arquitectura

```
Flask + SQLite single-file (cuentas.db)
├── Sesiones de Flask (login compartido)
├── Backup en background thread (@before_request, cada 24hs)
├── Templates Jinja con Bootstrap 5
└── JS vanilla (sin framework)
```

**Por que SQLite**: una sola persona/equipo lo usa, datos pequenos (~140 clientes), simple para backup (un solo archivo).

**Por que Flask y no FastAPI**: PythonAnywhere soporta Flask out-of-the-box, no necesitamos async, mas simple.

**Por que no React/Vue**: la app es chica, JS vanilla alcanza, evita complejidad de build.

## Datos del Excel de Magus

Importante: el Excel **no tiene encabezados**. Los datos arrancan en la fila 0.

| Col Excel | Indice | Que contiene |
|---|---|---|
| A | 0 | Codigo cliente (PK) |
| B | 1 | Nombre |
| D | 3 | Moneda (`$` o `U$S`) — filtramos solo `$` |
| F | 5 | Saldo +91 dias |
| G | 6 | Saldo 61-90 |
| I | 8 | Saldo 31-60 |
| J | 9 | Saldo 0-30 |
| M | 12 | Saldo total |

Columnas C, E, H, K, L se ignoran. Se filtran las filas con `B == "TOTAL"` y las filas vacias.

Hay 1 cliente en U$S (INQUILINO BAHIA BLANCA) que se ignora.

## Esquema de BD (SQLite)

Tablas (definidas en `init_db()`):

- `clientes` (codigo PK, nombre, saldos 0-30/31-60/61-90/91+/total, email, telefono, notas, fecha_actualizacion, fecha_ultimo_movimiento)
- `historial_contacto` (cliente_codigo, fecha_contacto, contactado_por, respuesta, comentario, proxima_fecha, **borrado** flag para soft delete, fecha_borrado, created_at)
- `cargas_excel` (registro de cada carga: nombre_archivo, cantidad_clientes, fecha)
- `historial_saldos` (diffs entre cargas para mostrar en pantalla de actualizaciones)
- `emails_equipo` (email, nombre, activo) — emails a los que enviar invitaciones de calendar

Hay migraciones idempotentes con `add_column_if_missing` para evolucionar el esquema sin romper bases existentes.

## Autenticacion

**Un solo usuario compartido** (decision de producto: equipo chico, no quieren gestionar logins por persona).

Archivos:
- `login_config.json` (gitignored): `{usuario, password_hash (werkzeug), secret_key (Flask sessions)}`
- En el primer arranque, si no existe → redirige a `/setup` para crear el usuario

Decorators:
- `@login_required` — rutas de paginas (redirige a /login)
- `@api_login_required` — endpoints API (devuelve 401)

Hay 1 endpoint sin proteger: `/api/cambiar-password` lo agregue con decorador (revisar al modificar codigo).

## Envio de emails (Calendar)

NO usamos Google Calendar API directamente. Usamos **SMTP + archivo .ics adjunto**.

- Cuenta de envio: `enviadorreuniones@gmail.com` (creada solo para esto)
- Config: `smtp_config.json` con `servidor`, `puerto`, `usuario`, `password` (app password de Gmail, 16 chars sin espacios)
- El .ics es generado en `crear_ics()` en `app.py`
- Default: evento de 30 min a las 9:00 hs del dia seleccionado, timezone America/Argentina/Buenos_Aires

Quien recibe los emails: emails marcados en el modal del cliente. Vienen de la tabla `emails_equipo` + opcionalmente el email del cliente si esta cargado.

## Backup a Google Drive

**Usamos OAuth, NO cuenta de servicio.**

Por que: las cuentas de servicio no tienen storage quota en Drive. Solo pueden subir a Shared Drives (que son de Workspace pago) o impersonando un usuario con domain-wide delegation. OAuth con consent del usuario es lo mas simple para esta escala.

Archivos:
- `oauth_client_secret.json` — credenciales de OAuth client (de Google Cloud Console)
- `drive_token.json` — token de refresh generado tras autorizar (con `setup_oauth.py` corrido localmente, abre browser)
- `drive_config.json` — `{folder_id}` de la carpeta destino en Drive
- `google_credentials.json` — cuenta de servicio LEGACY (no se usa pero esta en el repo por compat)

Backup automatico:
- `@before_request` chequea si paso `BACKUP_INTERVAL_HOURS` (24) desde el ultimo
- Si si, lanza thread daemon que ejecuta `hacer_backup()` de `backup_drive.py`
- Estado guardado en `backup_status.json`
- Limita 10 backups locales y 12 en Drive (rota automaticamente)

Backup manual: endpoint `/api/backup-manual` (POST), boton en navbar.

PythonAnywhere free **no tiene scheduled tasks** (requiere plan pago). Por eso el backup es triggereado por el uso.

## Deployment

**Hosting**: PythonAnywhere free tier (`tutextil.pythonanywhere.com`)
- Plan free: 512MB disk, 1 web app, no scheduled tasks, no dominio propio
- WSGI configurado en `/var/www/tutextil_pythonanywhere_com_wsgi.py` (importa `app` desde `app.py`)
- Path en server: `/home/tutextil/cuentas_corrientes/`

Workflow para deployar un cambio:
1. Editar local
2. Probar con `python app.py` o `iniciar.bat`
3. Commit + push a GitHub
4. **Subir archivos modificados manualmente** a PythonAnywhere via Files (no hay git pull automatico)
5. En tab "Web" de PythonAnywhere → click "Reload"

Para cambios grandes, generar nuevo `deploy_package.zip` y subir/extraer.

## Estilo de UI

- **Espanol en toda la UI** (rotulos, mensajes, errores)
- **Bootstrap 5** + Bootstrap Icons (CDN)
- Color primario: azul Bootstrap, gradient morado para login (`#667eea` → `#764ba2`)
- Botones flotantes (FAB) abajo a la derecha, apilados verticalmente
- Modales para acciones (no paginas nuevas para todo)
- Loading states con spinners en botones que disparan acciones async

## Convenciones de codigo

- Endpoints API en `/api/...`, paginas en `/...`
- Endpoints API devuelven JSON, paginas devuelven HTML
- Errores siempre devuelven `{error: "..."}` con status 4xx/5xx
- Path params: `<path:codigo>` (no `<string:codigo>`) porque los codigos de cliente pueden tener caracteres especiales
- `escapeHtml()` en JS para todo lo que viene de la BD antes de meter en innerHTML
- Money formateado con `formatMoney()` que usa `toLocaleString('es-AR')`

## Cosas a tener en cuenta

### Si me piden agregar un nuevo endpoint API
- Agregar `@api_login_required` despues de `@app.route(...)`
- Devolver JSON consistente con el resto

### Si me piden agregar una nueva pagina
- Crear template en `templates/`
- Agregar ruta con `@login_required`
- Agregar JS en `static/js/` (un archivo por pagina)
- Incluir navbar con boton de logout

### Si me piden agregar columna a `clientes` o `historial_contacto`
- Agregar al `CREATE TABLE` en `init_db()` (para bases nuevas)
- Agregar `add_column_if_missing(...)` para no romper bases existentes
- Si es nullable y tiene default, no romper APIs existentes

### Si el Excel de Magus cambia
- Las columnas estan hardcodeadas por indice en `parse_excel()`
- Verificar nuevamente columnas vs lo que viene en el Excel
- Mantener filtro `df[3] == '$'` solo pesos

### Sobre los archivos sensibles
- NUNCA commitearlos. Ya estan en `.gitignore`:
  - `smtp_config.json`, `login_config.json`, `oauth_client_secret.json`, `drive_token.json`, `drive_config.json`, `google_credentials.json`, `database/`, `uploads/`, `exports/`, `backups/`, `backup_status.json`
- Cuando hay que regenerar credenciales (`setup_oauth.py`) hay que correrlo LOCAL no en server (necesita browser)

### Sobre el plan free de PythonAnywhere
- Sin scheduled tasks (por eso backup en `@before_request`)
- Sin custom domain (URL es `tutextil.pythonanywhere.com`)
- 512MB disco — vigilar que `uploads/` y `backups/` no crezcan demasiado
- App se "duerme" si no hay trafico → primer request del dia puede ser lento

## Personas en el contexto del negocio

Equipo (en `EQUIPO` de `app.py`): Marina, Alberto, Juan Fanti, Romina, Fabiana, Sergio, Otro

Emails iniciales en la BD (`EMAILS_INICIALES`):
- fabiana.galaratti@gmail.com
- romizub@gmail.com
- sergio@tucumantextil.com
- albertojota2020@gmail.com

## Decisiones de producto importantes (no romper)

1. **Soft delete en historial_contacto**: cuando se borra, queda visible tachado en rojo con badge BORRADO. Esto es a proposito (auditabilidad).

2. **Contactado se calcula dinamico**: la columna "contactado" en la grilla es `EXISTS (historial_contacto desde la ultima carga de Excel)`. NO es una columna persistida.

3. **Filtros de "Contactados" y "Sin contactar"** son las stat cards de la pantalla principal — se clickean para filtrar.

4. **Solo clientes en pesos**: aunque haya algun cliente en USD en el Excel, se filtran.

5. **Saldos negativos se muestran**: clientes con saldo a favor (negativo) tambien estan en la grilla.

6. **Sin pre-confirmacion al cargar Excel**: si lo cargan, se aplican los cambios directo. Hay pantalla de "actualizaciones" para ver QUE cambio, no para confirmar antes.

7. **Una sola moneda (pesos)**: si en el futuro se quieren agregar otras monedas, hay que repensar el esquema.

## Cosas que estan a medio camino o pendientes

- Si Maru sube un Excel "viejo" (con fecha anterior al ultimo), igual se carga y "actualiza" la base. No hay validacion de fecha. Puede llevar a inconsistencias.
- Los backups quedan solo localmente si no esta `drive_token.json` o `drive_config.json` — silent fallback.
- No hay forma de eliminar un cliente que ya no esta. Si se va del Excel queda en la BD con saldo 0.
- El boton de "exportar" solo exporta: codigo, nombre, telefono, email, notas. No exporta saldos.
