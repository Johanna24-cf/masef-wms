from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id TEXT PRIMARY KEY,
            codigo TEXT NOT NULL,
            descripcion TEXT,
            contenedor TEXT,
            status TEXT,
            fv TEXT,
            qty INTEGER DEFAULT 0,
            qty_in INTEGER DEFAULT 0,
            fech_ing TEXT,
            categoria TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id TEXT PRIMARY KEY,
            fecha TEXT NOT NULL,
            codigo TEXT,
            descripcion TEXT,
            categoria TEXT,
            qty INTEGER,
            tipo TEXT,
            guia TEXT,
            fv TEXT,
            contenedor TEXT,
            origen TEXT,
            estado TEXT,
            distribuidor TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            label TEXT
        );

        CREATE TABLE IF NOT EXISTS packing_list (
            id TEXT PRIMARY KEY,
            cod TEXT,
            descripcion TEXT,
            contenedor TEXT,
            qty_pl INTEGER DEFAULT 0,
            qty_in INTEGER DEFAULT 0,
            dif INTEGER DEFAULT 0,
            fecha_ing TEXT,
            estado TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS informes (
            id TEXT PRIMARY KEY,
            tipo TEXT,
            fecha TEXT,
            datos JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Usuarios por defecto
    cur.execute("""
        INSERT INTO usuarios (usuario, password, rol, label) VALUES
            ('admin', '123', 'almacen', 'Administrador'),
            ('ClienteMasef', 'CF_Masef', 'cliente', 'Cliente MASEF')
        ON CONFLICT (usuario) DO NOTHING;
    """)

    conn.commit()
    cur.close()
    conn.close()

# ── SERVIR HTML ────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ── AUTH ───────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    usuario = data.get('usuario', '').strip()
    password = data.get('password', '')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario = %s AND password = %s", (usuario, password))
    user = cur.fetchone()
    cur.close(); conn.close()
    if user:
        return jsonify({'ok': True, 'rol': user['rol'], 'label': user['label']})
    return jsonify({'ok': False, 'msg': 'Usuario o contraseña incorrectos'}), 401

# ── STOCK ──────────────────────────────────────────────
@app.route('/api/stock', methods=['GET'])
def get_stock():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM stock ORDER BY codigo, contenedor")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stock', methods=['POST'])
def add_stock():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO stock (id, codigo, descripcion, contenedor, status, fv, qty, qty_in, fech_ing, categoria)
        VALUES (%(id)s, %(codigo)s, %(descripcion)s, %(contenedor)s, %(status)s, %(fv)s, %(qty)s, %(qty_in)s, %(fech_ing)s, %(categoria)s)
        ON CONFLICT (id) DO UPDATE SET
            qty = EXCLUDED.qty, status = EXCLUDED.status, updated_at = NOW()
    """, data)
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/stock/bulk', methods=['POST'])
def bulk_stock():
    items = request.json
    conn = get_db()
    cur = conn.cursor()
    for item in items:
        cur.execute("""
            INSERT INTO stock (id, codigo, descripcion, contenedor, status, fv, qty, qty_in, fech_ing, categoria)
            VALUES (%(id)s, %(codigo)s, %(descripcion)s, %(contenedor)s, %(status)s, %(fv)s, %(qty)s, %(qty_in)s, %(fech_ing)s, %(categoria)s)
            ON CONFLICT (id) DO UPDATE SET
                qty = EXCLUDED.qty, qty_in = EXCLUDED.qty_in,
                status = EXCLUDED.status, updated_at = NOW()
        """, item)
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'count': len(items)})

@app.route('/api/stock/<stock_id>', methods=['PATCH'])
def update_stock(stock_id):
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE stock SET qty = qty + %(delta)s, updated_at = NOW() WHERE id = %(id)s",
                {'delta': data.get('delta', 0), 'id': stock_id})
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ── MOVIMIENTOS ────────────────────────────────────────
@app.route('/api/movimientos', methods=['GET'])
def get_movimientos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM movimientos ORDER BY fecha, id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/movimientos', methods=['POST'])
def add_movimiento():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO movimientos (id, fecha, codigo, descripcion, categoria, qty, tipo, guia, fv, contenedor, origen, estado, distribuidor)
        VALUES (%(id)s, %(fecha)s, %(codigo)s, %(descripcion)s, %(categoria)s, %(qty)s, %(tipo)s, %(guia)s, %(fv)s, %(contenedor)s, %(origen)s, %(estado)s, %(distribuidor)s)
        ON CONFLICT (id) DO NOTHING
    """, data)
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/movimientos/bulk', methods=['POST'])
def bulk_movimientos():
    items = request.json
    conn = get_db()
    cur = conn.cursor()
    for item in items:
        cur.execute("""
            INSERT INTO movimientos (id, fecha, codigo, descripcion, categoria, qty, tipo, guia, fv, contenedor, origen, estado, distribuidor)
            VALUES (%(id)s, %(fecha)s, %(codigo)s, %(descripcion)s, %(categoria)s, %(qty)s, %(tipo)s, %(guia)s, %(fv)s, %(contenedor)s, %(origen)s, %(estado)s, %(distribuidor)s)
            ON CONFLICT (id) DO NOTHING
        """, item)
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'count': len(items)})

# ── DESPACHOS ──────────────────────────────────────────
@app.route('/api/despacho', methods=['POST'])
def registrar_despacho():
    data = request.json
    # data: { stock_id, qty, guia, fecha, codigo, desc, contenedor, fv, distribuidor }
    conn = get_db()
    cur = conn.cursor()

    # Verificar stock disponible
    cur.execute("SELECT qty FROM stock WHERE id = %s", (data['stock_id'],))
    row = cur.fetchone()
    if not row:
        return jsonify({'ok': False, 'msg': 'Stock no encontrado'}), 404
    if row['qty'] < data['qty']:
        return jsonify({'ok': False, 'msg': f'Stock insuficiente. Disponible: {row["qty"]}'}), 400

    # Descontar stock
    cur.execute("UPDATE stock SET qty = qty - %s, updated_at = NOW() WHERE id = %s",
                (data['qty'], data['stock_id']))

    # Registrar movimiento
    mov_id = f"MOV-DESP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cur.execute("""
        INSERT INTO movimientos (id, fecha, codigo, descripcion, categoria, qty, tipo, guia, fv, contenedor, origen, estado, distribuidor)
        VALUES (%s, %s, %s, %s, %s, %s, 'SALIDA', %s, %s, %s, 'STOCK_NUEVO', 'DISPONIBLE', %s)
    """, (mov_id, data['fecha'], data['codigo'], data['descripcion'], data.get('categoria',''),
          -abs(data['qty']), data['guia'], data.get('fv',''), data['contenedor'], data.get('distribuidor','')))

    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'mov_id': mov_id})

# ── MERMA ──────────────────────────────────────────────
@app.route('/api/baja-merma', methods=['POST'])
def baja_merma():
    data = request.json
    # data: { lineas: [{stock_id, qty, motivo}], fecha, informe_id }
    conn = get_db()
    cur = conn.cursor()
    for linea in data['lineas']:
        cur.execute("UPDATE stock SET qty = qty - %s, updated_at = NOW() WHERE id = %s",
                    (linea['qty'], linea['stock_id']))
        mov_id = f"MOV-BAJA-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        cur.execute("""
            INSERT INTO movimientos (id, fecha, codigo, descripcion, categoria, qty, tipo, guia, fv, contenedor, origen, estado, distribuidor)
            SELECT %s, %s, codigo, descripcion, categoria, -%s, 'MERMA', %s, fv, contenedor, 'STOCK_NUEVO', 'MERMA', ''
            FROM stock WHERE id = %s
        """, (mov_id, data['fecha'], linea['qty'], data.get('informe_id','BAJA'), linea['stock_id']))

    # Guardar informe
    cur.execute("""
        INSERT INTO informes (id, tipo, fecha, datos)
        VALUES (%s, 'BAJA', %s, %s)
    """, (data['informe_id'], data['fecha'], json.dumps(data['lineas'])))

    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ── PACKING LIST ───────────────────────────────────────
@app.route('/api/packing', methods=['GET'])
def get_packing():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM packing_list ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/packing', methods=['POST'])
def add_packing():
    items = request.json  # lista de items
    conn = get_db()
    cur = conn.cursor()
    for item in items:
        item_id = f"PL-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{item.get('cod','')}"
        cur.execute("""
            INSERT INTO packing_list (id, cod, descripcion, contenedor, qty_pl, qty_in, dif, fecha_ing, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (item_id, item['cod'], item['descripcion'], item['contenedor'],
              item['qty_pl'], item['qty_in'], item['dif'], item['fecha_ing'], item.get('estado','REVISADO')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ── AJUSTES ────────────────────────────────────────────
@app.route('/api/ajuste', methods=['POST'])
def ajuste():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE stock SET qty = qty + %s, updated_at = NOW() WHERE id = %s",
                (data['delta'], data['stock_id']))
    mov_id = f"MOV-AJ-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    tipo = 'AJUSTE-IN' if data['delta'] > 0 else 'AJUSTE-OUT'
    cur.execute("""
        INSERT INTO movimientos (id, fecha, codigo, descripcion, categoria, qty, tipo, guia, fv, contenedor, origen, estado, distribuidor)
        SELECT %s, %s, codigo, descripcion, categoria, %s, %s, %s, fv, contenedor, 'STOCK_NUEVO', status, ''
        FROM stock WHERE id = %s
    """, (mov_id, data['fecha'], data['delta'], tipo, data.get('motivo','AJUSTE'), data['stock_id']))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ── INIT ───────────────────────────────────────────────

@app.route('/api/init', methods=['GET'])
def force_init():
    try:
        init_db()
        return jsonify({'ok': True, 'msg': 'Tablas creadas correctamente'})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

try:
    init_db()
except Exception as e:
    print(f"DB init warning: {e}")
