"""
Cuentas Corrientes - Tu Textil
Aplicacion para gestionar cobranzas de clientes.
"""

import os
import json
import sqlite3
import smtplib
import uuid
import secrets
from functools import wraps
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'cuentas.db')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
SMTP_CONFIG_PATH = os.path.join(BASE_DIR, 'smtp_config.json')
LOGIN_CONFIG_PATH = os.path.join(BASE_DIR, 'login_config.json')

# Personas del equipo (para registrar quien contacto al cliente)
EQUIPO = ['Marina', 'Alberto', 'Juan Fanti', 'Romina', 'Fabiana', 'Sergio', 'Otro']

# Opciones de respuesta del cliente
RESPUESTAS_CLIENTE = [
    'Va a pagar',
    'Que vuelva a contactar',
    'Me contacte y no tuve respuesta',
    'Deje mensaje',
    'No me pude contactar',
    'Pago parcial',
    'En disputa',
    'Otro'
]

# Emails iniciales del equipo (se cargan en la BD la primera vez)
EMAILS_INICIALES = [
    'fabiana.galaratti@gmail.com',
    'romizub@gmail.com',
    'sergio@tucumantextil.com',
    'albertojota2020@gmail.com',
]


def get_db():
    """Obtener conexion a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Inicializar la base de datos con las tablas necesarias."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS clientes (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            saldo_0_30 REAL DEFAULT 0,
            saldo_31_60 REAL DEFAULT 0,
            saldo_61_90 REAL DEFAULT 0,
            saldo_91_mas REAL DEFAULT 0,
            saldo_total REAL DEFAULT 0,
            email TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            notas TEXT DEFAULT '',
            fecha_actualizacion TEXT,
            fecha_ultimo_movimiento TEXT
        );

        CREATE TABLE IF NOT EXISTS historial_contacto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_codigo TEXT NOT NULL,
            fecha_contacto TEXT NOT NULL,
            contactado_por TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            comentario TEXT DEFAULT '',
            proxima_fecha TEXT,
            borrado INTEGER DEFAULT 0,
            fecha_borrado TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (cliente_codigo) REFERENCES clientes(codigo)
        );

        CREATE TABLE IF NOT EXISTS cargas_excel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_carga TEXT DEFAULT (datetime('now', 'localtime')),
            nombre_archivo TEXT,
            cantidad_clientes INTEGER,
            archivo_path TEXT
        );

        CREATE TABLE IF NOT EXISTS historial_saldos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carga_id INTEGER,
            cliente_codigo TEXT,
            saldo_0_30_anterior REAL,
            saldo_31_60_anterior REAL,
            saldo_61_90_anterior REAL,
            saldo_91_mas_anterior REAL,
            saldo_total_anterior REAL,
            saldo_0_30_nuevo REAL,
            saldo_31_60_nuevo REAL,
            saldo_61_90_nuevo REAL,
            saldo_91_mas_nuevo REAL,
            saldo_total_nuevo REAL,
            tipo_cambio TEXT,
            FOREIGN KEY (carga_id) REFERENCES cargas_excel(id),
            FOREIGN KEY (cliente_codigo) REFERENCES clientes(codigo)
        );

        CREATE TABLE IF NOT EXISTS emails_equipo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            nombre TEXT DEFAULT '',
            activo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
    ''')

    # Migraciones: agregar columnas si no existen (para bases antiguas)
    def add_column_if_missing(table, column, definition):
        cols = [r['name'] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()]
        if column not in cols:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

    add_column_if_missing('clientes', 'fecha_ultimo_movimiento', 'TEXT')
    add_column_if_missing('historial_contacto', 'borrado', 'INTEGER DEFAULT 0')
    add_column_if_missing('historial_contacto', 'fecha_borrado', 'TEXT')

    # Cargar emails iniciales si la tabla esta vacia
    count = conn.execute('SELECT COUNT(*) as c FROM emails_equipo').fetchone()['c']
    if count == 0:
        for email in EMAILS_INICIALES:
            conn.execute(
                'INSERT OR IGNORE INTO emails_equipo (email) VALUES (?)', (email,)
            )

    conn.commit()
    conn.close()


def parse_excel(filepath):
    """Parsear el Excel de Magus y devolver datos limpios."""
    df = pd.read_excel(filepath, header=None)

    # Filtrar: solo pesos (columna 3 == '$'), ignorar TOTAL y filas vacias
    df = df[df[3] == '$'].copy()
    df = df[df[1] != 'TOTAL'].copy()
    df = df[df[0].notna()].copy()

    clientes = []
    for _, row in df.iterrows():
        clientes.append({
            'codigo': str(row[0]).strip(),
            'nombre': str(row[1]).strip() if pd.notna(row[1]) else '',
            'saldo_91_mas': float(row[5]) if pd.notna(row[5]) else 0.0,
            'saldo_61_90': float(row[6]) if pd.notna(row[6]) else 0.0,
            'saldo_31_60': float(row[8]) if pd.notna(row[8]) else 0.0,
            'saldo_0_30': float(row[9]) if pd.notna(row[9]) else 0.0,
            'saldo_total': float(row[12]) if pd.notna(row[12]) else 0.0,
        })

    return clientes


def get_smtp_config():
    """Cargar configuracion SMTP."""
    if os.path.exists(SMTP_CONFIG_PATH):
        with open(SMTP_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


# ============================================================
# LOGIN
# ============================================================

def get_login_config():
    """Cargar configuracion de login. Devuelve None si no esta seteado."""
    if os.path.exists(LOGIN_CONFIG_PATH):
        with open(LOGIN_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_login_config(config):
    """Guardar configuracion de login."""
    with open(LOGIN_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def init_secret_key():
    """Inicializar secret key para sesiones. Persistente en login_config.json."""
    config = get_login_config()
    if config and 'secret_key' in config:
        app.secret_key = config['secret_key']
    else:
        # Generar secret key temporal (se reemplaza cuando se setea el password)
        app.secret_key = secrets.token_hex(32)


def login_required(f):
    """Decorator para rutas que requieren login (paginas)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Si no hay password configurado, redirigir al setup
        if not get_login_config():
            return redirect(url_for('setup'))
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    """Decorator para endpoints API (devuelve 401 en vez de redirigir)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_login_config():
            return jsonify({'error': 'App no configurada'}), 401
        if not session.get('logged_in'):
            return jsonify({'error': 'No autenticado'}), 401
        return f(*args, **kwargs)
    return decorated


# Rutas de autenticacion ----------------------------------------

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Primera vez: definir usuario y password."""
    if get_login_config():
        return redirect(url_for('login'))

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not usuario or not password:
            return render_template('setup.html', error='Completa usuario y contrasena')
        if password != password2:
            return render_template('setup.html', error='Las contrasenas no coinciden')
        if len(password) < 6:
            return render_template('setup.html', error='La contrasena debe tener al menos 6 caracteres')

        config = {
            'usuario': usuario,
            'password_hash': generate_password_hash(password),
            'secret_key': secrets.token_hex(32)
        }
        save_login_config(config)
        app.secret_key = config['secret_key']

        session.permanent = True
        session['logged_in'] = True
        session['usuario'] = usuario
        return redirect(url_for('index'))

    return render_template('setup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Pantalla de login."""
    if not get_login_config():
        return redirect(url_for('setup'))

    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')
        recordar = request.form.get('recordar') == 'on'

        config = get_login_config()
        if (usuario == config['usuario'] and
                check_password_hash(config['password_hash'], password)):
            session.permanent = recordar
            session['logged_in'] = True
            session['usuario'] = usuario
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        else:
            return render_template('login.html', error='Usuario o contrasena incorrectos')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/cambiar-password', methods=['POST'])
@api_login_required
def api_cambiar_password():
    """Cambiar la contrasena del usuario."""
    data = request.json
    password_actual = data.get('password_actual', '')
    password_nuevo = data.get('password_nuevo', '')

    config = get_login_config()
    if not check_password_hash(config['password_hash'], password_actual):
        return jsonify({'error': 'Contrasena actual incorrecta'}), 400
    if len(password_nuevo) < 6:
        return jsonify({'error': 'La nueva contrasena debe tener al menos 6 caracteres'}), 400

    config['password_hash'] = generate_password_hash(password_nuevo)
    save_login_config(config)
    return jsonify({'ok': True})


# ============================================================
# RUTAS - PAGINAS
# ============================================================

@app.route('/')
@login_required
def index():
    """Pantalla principal."""
    return render_template('principal.html', usuario=session.get('usuario', ''))


@app.route('/cliente/<path:codigo>')
@login_required
def detalle_cliente(codigo):
    """Pantalla de detalle del cliente."""
    return render_template('detalle_cliente.html', codigo=codigo, usuario=session.get('usuario', ''))


@app.route('/actualizaciones/<int:carga_id>')
@login_required
def actualizaciones(carga_id):
    """Pantalla de actualizaciones (comparacion de Excel)."""
    return render_template('actualizaciones.html', carga_id=carga_id, usuario=session.get('usuario', ''))


# ============================================================
# API - CLIENTES
# ============================================================

@app.route('/api/clientes', methods=['GET'])
@api_login_required
def api_clientes():
    """Obtener lista de clientes con filtros opcionales."""
    conn = get_db()
    filtro = request.args.get('filtro', '')
    contacto_filtro = request.args.get('contacto', '')  # 'si', 'no' o ''
    busqueda = request.args.get('busqueda', '')

    query = '''
        SELECT c.*,
            CASE WHEN EXISTS (
                SELECT 1 FROM historial_contacto hc
                JOIN cargas_excel ce ON ce.id = (SELECT MAX(id) FROM cargas_excel)
                WHERE hc.cliente_codigo = c.codigo
                AND hc.created_at >= ce.fecha_carga
                AND hc.borrado = 0
            ) THEN 1 ELSE 0 END as contactado
        FROM clientes c
        WHERE 1=1
    '''
    params = []

    if busqueda:
        query += ' AND (c.codigo LIKE ? OR LOWER(c.nombre) LIKE LOWER(?))'
        params.extend([f'%{busqueda}%', f'%{busqueda}%'])

    if filtro == '0-30':
        query += ' AND c.saldo_0_30 != 0'
    elif filtro == '31-60':
        query += ' AND c.saldo_31_60 != 0'
    elif filtro == '61-90':
        query += ' AND c.saldo_61_90 != 0'
    elif filtro == '91+':
        query += ' AND c.saldo_91_mas != 0'

    query += ' ORDER BY c.saldo_total DESC'

    clientes = conn.execute(query, params).fetchall()
    clientes = [dict(c) for c in clientes]

    # Filtro de contactado/sin contactar (post-query porque depende del calculo)
    if contacto_filtro == 'si':
        clientes = [c for c in clientes if c['contactado'] == 1]
    elif contacto_filtro == 'no':
        clientes = [c for c in clientes if c['contactado'] == 0]

    conn.close()

    return jsonify(clientes)


@app.route('/api/cliente/<path:codigo>', methods=['GET'])
@api_login_required
def api_cliente_detalle(codigo):
    """Obtener detalle de un cliente."""
    conn = get_db()
    cliente = conn.execute('SELECT * FROM clientes WHERE codigo = ?', (codigo,)).fetchone()
    conn.close()

    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404

    return jsonify(dict(cliente))


@app.route('/api/cliente/<path:codigo>/contacto', methods=['PUT'])
@api_login_required
def api_actualizar_contacto(codigo):
    """Actualizar datos de contacto de un cliente."""
    data = request.json
    conn = get_db()

    conn.execute('''
        UPDATE clientes SET email = ?, telefono = ?, notas = ?
        WHERE codigo = ?
    ''', (data.get('email', ''), data.get('telefono', ''), data.get('notas', ''), codigo))

    conn.commit()
    conn.close()

    return jsonify({'ok': True})


# ============================================================
# API - HISTORIAL DE CONTACTO
# ============================================================

@app.route('/api/cliente/<path:codigo>/historial', methods=['GET'])
@api_login_required
def api_historial(codigo):
    """Obtener historial de contacto de un cliente (incluye borrados)."""
    conn = get_db()
    historial = conn.execute('''
        SELECT * FROM historial_contacto
        WHERE cliente_codigo = ?
        ORDER BY fecha_contacto DESC, created_at DESC
    ''', (codigo,)).fetchall()
    conn.close()

    return jsonify([dict(h) for h in historial])


@app.route('/api/cliente/<path:codigo>/historial', methods=['POST'])
@api_login_required
def api_agregar_contacto(codigo):
    """Agregar nueva entrada al historial de contacto."""
    data = request.json
    conn = get_db()

    conn.execute('''
        INSERT INTO historial_contacto
        (cliente_codigo, fecha_contacto, contactado_por, respuesta, comentario, proxima_fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        codigo,
        data['fecha_contacto'],
        data['contactado_por'],
        data['respuesta'],
        data.get('comentario', ''),
        data.get('proxima_fecha', '')
    ))

    conn.commit()
    conn.close()

    return jsonify({'ok': True})


@app.route('/api/historial/<int:historial_id>', methods=['DELETE'])
@api_login_required
def api_borrar_contacto(historial_id):
    """Borrado logico de una entrada del historial."""
    conn = get_db()
    conn.execute('''
        UPDATE historial_contacto
        SET borrado = 1, fecha_borrado = datetime('now', 'localtime')
        WHERE id = ?
    ''', (historial_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ============================================================
# API - EMAILS DEL EQUIPO
# ============================================================

@app.route('/api/emails-equipo', methods=['GET'])
@api_login_required
def api_emails_equipo():
    """Obtener lista de emails del equipo."""
    conn = get_db()
    emails = conn.execute(
        'SELECT * FROM emails_equipo WHERE activo = 1 ORDER BY email'
    ).fetchall()
    conn.close()
    return jsonify([dict(e) for e in emails])


@app.route('/api/emails-equipo', methods=['POST'])
@api_login_required
def api_agregar_email():
    """Agregar nuevo email al equipo."""
    data = request.json
    email = data.get('email', '').strip()
    nombre = data.get('nombre', '').strip()

    if not email or '@' not in email:
        return jsonify({'error': 'Email invalido'}), 400

    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO emails_equipo (email, nombre) VALUES (?, ?)',
            (email, nombre)
        )
        conn.commit()
        return jsonify({'ok': True})
    except sqlite3.IntegrityError:
        # Si ya existe, reactivarlo
        conn.execute(
            'UPDATE emails_equipo SET activo = 1 WHERE email = ?', (email,)
        )
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


@app.route('/api/emails-equipo/<int:email_id>', methods=['DELETE'])
@api_login_required
def api_borrar_email(email_id):
    """Borrar un email del equipo (logico)."""
    conn = get_db()
    conn.execute('UPDATE emails_equipo SET activo = 0 WHERE id = ?', (email_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ============================================================
# API - CARGA DE EXCEL
# ============================================================

@app.route('/api/info', methods=['GET'])
@api_login_required
def api_info():
    """Obtener informacion general de la app."""
    conn = get_db()
    ultima_carga = conn.execute(
        'SELECT * FROM cargas_excel ORDER BY id DESC LIMIT 1'
    ).fetchone()
    total_clientes = conn.execute('SELECT COUNT(*) as total FROM clientes').fetchone()
    conn.close()

    smtp = get_smtp_config()

    return jsonify({
        'ultima_carga': dict(ultima_carga) if ultima_carga else None,
        'total_clientes': total_clientes['total'] if total_clientes else 0,
        'equipo': EQUIPO,
        'respuestas': RESPUESTAS_CLIENTE,
        'smtp_configurado': smtp is not None and smtp.get('password', '') != ''
    })


@app.route('/api/cargar-excel', methods=['POST'])
@api_login_required
def api_cargar_excel():
    """Cargar un nuevo Excel y comparar con datos existentes."""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envio archivo'}), 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'Nombre de archivo vacio'}), 400

    # Guardar archivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_guardado = f"{timestamp}_{archivo.filename}"
    filepath = os.path.join(UPLOADS_DIR, nombre_guardado)
    archivo.save(filepath)

    try:
        nuevos_clientes = parse_excel(filepath)
    except Exception as e:
        return jsonify({'error': f'Error al leer el Excel: {str(e)}'}), 400

    conn = get_db()
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Verificar si es la primera carga
    existe_data = conn.execute('SELECT COUNT(*) as c FROM clientes').fetchone()['c']
    es_primera_carga = existe_data == 0

    # Registrar la carga
    cursor = conn.execute('''
        INSERT INTO cargas_excel (nombre_archivo, cantidad_clientes, archivo_path)
        VALUES (?, ?, ?)
    ''', (archivo.filename, len(nuevos_clientes), filepath))
    carga_id = cursor.lastrowid

    cambios = []

    if es_primera_carga:
        # Primera carga: insertar todos los clientes
        for c in nuevos_clientes:
            conn.execute('''
                INSERT OR REPLACE INTO clientes
                (codigo, nombre, saldo_0_30, saldo_31_60, saldo_61_90, saldo_91_mas, saldo_total,
                 fecha_actualizacion, fecha_ultimo_movimiento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (c['codigo'], c['nombre'], c['saldo_0_30'], c['saldo_31_60'],
                  c['saldo_61_90'], c['saldo_91_mas'], c['saldo_total'], ahora, ahora))
    else:
        # Carga posterior: comparar y registrar cambios
        for c in nuevos_clientes:
            anterior = conn.execute(
                'SELECT * FROM clientes WHERE codigo = ?', (c['codigo'],)
            ).fetchone()

            if anterior:
                # Cliente existente - verificar cambios
                hubo_cambio = (
                    anterior['saldo_0_30'] != c['saldo_0_30'] or
                    anterior['saldo_31_60'] != c['saldo_31_60'] or
                    anterior['saldo_61_90'] != c['saldo_61_90'] or
                    anterior['saldo_91_mas'] != c['saldo_91_mas'] or
                    anterior['saldo_total'] != c['saldo_total']
                )

                if hubo_cambio:
                    tipo = 'pago_total' if c['saldo_total'] == 0 else 'cambio_saldo'
                    conn.execute('''
                        INSERT INTO historial_saldos
                        (carga_id, cliente_codigo,
                         saldo_0_30_anterior, saldo_31_60_anterior, saldo_61_90_anterior,
                         saldo_91_mas_anterior, saldo_total_anterior,
                         saldo_0_30_nuevo, saldo_31_60_nuevo, saldo_61_90_nuevo,
                         saldo_91_mas_nuevo, saldo_total_nuevo, tipo_cambio)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (carga_id, c['codigo'],
                          anterior['saldo_0_30'], anterior['saldo_31_60'],
                          anterior['saldo_61_90'], anterior['saldo_91_mas'],
                          anterior['saldo_total'],
                          c['saldo_0_30'], c['saldo_31_60'],
                          c['saldo_61_90'], c['saldo_91_mas'],
                          c['saldo_total'], tipo))

                    cambios.append({
                        'codigo': c['codigo'],
                        'nombre': c['nombre'],
                        'tipo': tipo,
                        'saldo_anterior': anterior['saldo_total'],
                        'saldo_nuevo': c['saldo_total'],
                        'diferencia': c['saldo_total'] - anterior['saldo_total']
                    })

                # Actualizar saldos (mantener datos de contacto)
                # Si hubo cambio, actualizar fecha_ultimo_movimiento
                fecha_mov = ahora if hubo_cambio else anterior['fecha_ultimo_movimiento']
                conn.execute('''
                    UPDATE clientes SET
                        nombre = ?, saldo_0_30 = ?, saldo_31_60 = ?,
                        saldo_61_90 = ?, saldo_91_mas = ?, saldo_total = ?,
                        fecha_actualizacion = ?, fecha_ultimo_movimiento = ?
                    WHERE codigo = ?
                ''', (c['nombre'], c['saldo_0_30'], c['saldo_31_60'],
                      c['saldo_61_90'], c['saldo_91_mas'], c['saldo_total'],
                      ahora, fecha_mov, c['codigo']))
            else:
                # Cliente nuevo
                conn.execute('''
                    INSERT INTO clientes
                    (codigo, nombre, saldo_0_30, saldo_31_60, saldo_61_90,
                     saldo_91_mas, saldo_total, fecha_actualizacion, fecha_ultimo_movimiento)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (c['codigo'], c['nombre'], c['saldo_0_30'], c['saldo_31_60'],
                      c['saldo_61_90'], c['saldo_91_mas'], c['saldo_total'], ahora, ahora))

                cambios.append({
                    'codigo': c['codigo'],
                    'nombre': c['nombre'],
                    'tipo': 'nuevo',
                    'saldo_anterior': 0,
                    'saldo_nuevo': c['saldo_total'],
                    'diferencia': c['saldo_total']
                })

        # Detectar clientes que ya no aparecen en el nuevo Excel (pagaron todo)
        codigos_nuevos = {c['codigo'] for c in nuevos_clientes}
        todos_anteriores = conn.execute('SELECT codigo, nombre, saldo_total FROM clientes').fetchall()
        for ant in todos_anteriores:
            if ant['codigo'] not in codigos_nuevos and ant['saldo_total'] != 0:
                conn.execute('''
                    INSERT INTO historial_saldos
                    (carga_id, cliente_codigo,
                     saldo_0_30_anterior, saldo_31_60_anterior, saldo_61_90_anterior,
                     saldo_91_mas_anterior, saldo_total_anterior,
                     saldo_0_30_nuevo, saldo_31_60_nuevo, saldo_61_90_nuevo,
                     saldo_91_mas_nuevo, saldo_total_nuevo, tipo_cambio)
                    VALUES (?, ?,
                        (SELECT saldo_0_30 FROM clientes WHERE codigo = ?),
                        (SELECT saldo_31_60 FROM clientes WHERE codigo = ?),
                        (SELECT saldo_61_90 FROM clientes WHERE codigo = ?),
                        (SELECT saldo_91_mas FROM clientes WHERE codigo = ?),
                        (SELECT saldo_total FROM clientes WHERE codigo = ?),
                        0, 0, 0, 0, 0, 'pago_total')
                ''', (carga_id, ant['codigo'], ant['codigo'], ant['codigo'],
                      ant['codigo'], ant['codigo'], ant['codigo']))

                # Poner saldos en 0 y actualizar fecha de movimiento
                conn.execute('''
                    UPDATE clientes SET
                        saldo_0_30 = 0, saldo_31_60 = 0, saldo_61_90 = 0,
                        saldo_91_mas = 0, saldo_total = 0,
                        fecha_actualizacion = ?, fecha_ultimo_movimiento = ?
                    WHERE codigo = ?
                ''', (ahora, ahora, ant['codigo']))

                cambios.append({
                    'codigo': ant['codigo'],
                    'nombre': ant['nombre'],
                    'tipo': 'pago_total',
                    'saldo_anterior': ant['saldo_total'],
                    'saldo_nuevo': 0,
                    'diferencia': -ant['saldo_total']
                })

    conn.commit()
    conn.close()

    return jsonify({
        'ok': True,
        'carga_id': carga_id,
        'es_primera_carga': es_primera_carga,
        'total_clientes': len(nuevos_clientes),
        'total_cambios': len(cambios),
        'cambios': cambios
    })


# ============================================================
# API - ACTUALIZACIONES
# ============================================================

@app.route('/api/actualizaciones/<int:carga_id>', methods=['GET'])
@api_login_required
def api_actualizaciones(carga_id):
    """Obtener los cambios de una carga especifica."""
    conn = get_db()

    carga = conn.execute(
        'SELECT * FROM cargas_excel WHERE id = ?', (carga_id,)
    ).fetchone()

    cambios = conn.execute('''
        SELECT hs.*, c.nombre, c.email, c.telefono
        FROM historial_saldos hs
        JOIN clientes c ON c.codigo = hs.cliente_codigo
        WHERE hs.carga_id = ?
        ORDER BY ABS(hs.saldo_total_nuevo - hs.saldo_total_anterior) DESC
    ''', (carga_id,)).fetchall()

    conn.close()

    return jsonify({
        'carga': dict(carga) if carga else None,
        'cambios': [dict(c) for c in cambios]
    })


@app.route('/api/historial-cargas', methods=['GET'])
@api_login_required
def api_historial_cargas():
    """Obtener historial de cargas de Excel."""
    conn = get_db()
    cargas = conn.execute(
        'SELECT * FROM cargas_excel ORDER BY id DESC'
    ).fetchall()
    conn.close()

    return jsonify([dict(c) for c in cargas])


# ============================================================
# API - EXPORTAR
# ============================================================

@app.route('/api/exportar', methods=['GET'])
@api_login_required
def api_exportar():
    """Exportar clientes con datos de contacto a Excel.
    Solo columnas: codigo, nombre, telefono, email, notas."""
    conn = get_db()

    clientes = conn.execute('''
        SELECT codigo, nombre, telefono, email, notas
        FROM clientes
        ORDER BY nombre
    ''').fetchall()

    conn.close()

    df = pd.DataFrame([dict(c) for c in clientes])
    df.columns = ['Codigo', 'Nombre', 'Telefono', 'Email', 'Notas']

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'contactos_clientes_{timestamp}.xlsx'
    filepath = os.path.join(EXPORTS_DIR, filename)

    df.to_excel(filepath, index=False, engine='openpyxl')

    return send_file(filepath, as_attachment=True, download_name=filename)


# ============================================================
# API - RECORDATORIO (envio automatico via SMTP + ICS)
# ============================================================

def crear_ics(titulo, descripcion, fecha, emails_destino, organizador):
    """Crear contenido ICS para invitacion de calendario."""
    # fecha viene como YYYY-MM-DD, asumimos 9:00 hs por defecto, evento de 30 min
    dt_inicio = datetime.strptime(fecha, '%Y-%m-%d').replace(hour=9, minute=0)
    dt_fin = dt_inicio + timedelta(minutes=30)

    dtstamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    dtstart = dt_inicio.strftime('%Y%m%dT%H%M%S')
    dtend = dt_fin.strftime('%Y%m%dT%H%M%S')
    uid = str(uuid.uuid4()) + '@tutextil.com.ar'

    attendees = '\n'.join([
        f'ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{e}'
        for e in emails_destino
    ])

    # Escapar caracteres especiales en titulo y descripcion
    titulo_safe = titulo.replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')
    desc_safe = descripcion.replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Tu Textil//Cuentas Corrientes//ES
METHOD:REQUEST
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART;TZID=America/Argentina/Buenos_Aires:{dtstart}
DTEND;TZID=America/Argentina/Buenos_Aires:{dtend}
SUMMARY:{titulo_safe}
DESCRIPTION:{desc_safe}
ORGANIZER;CN=Cuentas Corrientes Tu Textil:mailto:{organizador}
{attendees}
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Recordatorio
TRIGGER:-PT30M
END:VALARM
END:VEVENT
END:VCALENDAR"""

    return ics


@app.route('/api/enviar-recordatorio', methods=['POST'])
@api_login_required
def api_enviar_recordatorio():
    """Enviar invitacion de calendar via SMTP con archivo ICS."""
    smtp_config = get_smtp_config()
    if not smtp_config or not smtp_config.get('password'):
        return jsonify({
            'error': 'SMTP no configurado. Configura primero el archivo smtp_config.json'
        }), 400

    data = request.json
    titulo = data.get('titulo', 'Recordatorio cobranza')
    descripcion = data.get('descripcion', '')
    fecha = data.get('fecha', '')
    emails = data.get('emails', [])

    if not fecha or not emails:
        return jsonify({'error': 'Falta fecha o emails'}), 400

    try:
        # Crear archivo ICS
        ics_content = crear_ics(
            titulo, descripcion, fecha, emails,
            smtp_config.get('usuario', '')
        )

        # Armar email
        msg = MIMEMultipart('mixed')
        msg['From'] = f"Cuentas Corrientes Tu Textil <{smtp_config['usuario']}>"
        msg['To'] = ', '.join(emails)
        msg['Subject'] = f'Recordatorio: {titulo}'

        # Cuerpo del email
        cuerpo = f"""Hola,

Te llego un recordatorio desde Cuentas Corrientes - Tu Textil.

Asunto: {titulo}
Fecha: {fecha}
{('Detalle: ' + descripcion) if descripcion else ''}

Aceptar la invitacion adjunta para que se agregue a tu calendar.

Saludos,
Tu Textil
"""
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Adjuntar ICS
        ics_part = MIMEBase('text', 'calendar', method='REQUEST', name='invite.ics')
        ics_part.set_payload(ics_content.encode('utf-8'))
        encoders.encode_base64(ics_part)
        ics_part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
        ics_part.add_header('Content-Class', 'urn:content-classes:calendarmessage')
        msg.attach(ics_part)

        # Enviar
        with smtplib.SMTP(smtp_config['servidor'], smtp_config['puerto']) as server:
            server.starttls()
            server.login(smtp_config['usuario'], smtp_config['password'])
            server.send_message(msg)

        return jsonify({
            'ok': True,
            'mensaje': f'Invitacion enviada a {len(emails)} destinatarios'
        })

    except Exception as e:
        return jsonify({'error': f'Error al enviar: {str(e)}'}), 500


# ============================================================
# INICIO
# ============================================================

# Inicializacion (corre tanto en local como en deployment)
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
init_db()
init_secret_key()

# Crear archivo de config SMTP si no existe
if not os.path.exists(SMTP_CONFIG_PATH):
    with open(SMTP_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'servidor': 'smtp.gmail.com',
            'puerto': 587,
            'usuario': 'enviadorreuniones@gmail.com',
            'password': ''
        }, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  CUENTAS CORRIENTES - Tu Textil")
    print("  Abri el navegador en: http://localhost:5050")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=5050, debug=True)
