from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# ─── DB CONNECTION ────────────────────────────────────────
def get_db():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')

# ─── INIT DB ─────────────────────────────────────────────
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id TEXT PRIMARY KEY,
            data JSONB NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS movimientos (
            id TEXT PRIMARY KEY,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS informes (
            id TEXT PRIMARY KEY,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS packing_list (
            id TEXT PRIMARY KEY,
            data JSONB NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS seed_data (
            key TEXT PRIMARY KEY,
            value JSONB NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# ─── SERVE FRONTEND ──────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# ─── AUTH ────────────────────────────────────────────────
USERS = {
    'admin':        {'pass': '123',      'role': 'almacen', 'label': 'Administrador'},
    'ClienteMasef': {'pass': 'CF_Masef', 'role': 'cliente', 'label': 'Cliente MASEF'},
}

@app.route('/api/login', methods=['POST'])
def login():
    body = request.get_json()
    user = body.get('user', '').strip()
    pwd  = body.get('pass', '')
    if user in USERS and USERS[user]['pass'] == pwd:
        u = USERS[user]
        return jsonify({'ok': True, 'role': u['role'], 'label': u['label']})
    return jsonify({'ok': False, 'error': 'Usuario o contraseña incorrectos'}), 401

# ─── SEED (carga inicial desde HTML) ─────────────────────
@app.route('/api/seed', methods=['POST'])
def seed():
    """Recibe los datos del HTML y los guarda en la BD si está vacía."""
    body = request.get_json()
    conn = get_db()
    cur  = conn.cursor()

    # Solo insertar si no hay datos
    cur.execute("SELECT COUNT(*) FROM stock;")
    count = cur.fetchone()[0]

    if count == 0:
        # Stock
        for item in body.get('stock', []):
            cur.execute(
                "INSERT INTO stock (id, data) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (item['id'], json.dumps(item))
            )
        # Movimientos
        for mov in body.get('movimientos', []):
            cur.execute(
                "INSERT INTO movimientos (id, data) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (mov['id'], json.dumps(mov))
            )
        # Packing list
        for i, pl in enumerate(body.get('packingList', [])):
            pk = pl.get('id') or f'PL-{i:04d}'
            cur.execute(
                "INSERT INTO packing_list (id, data) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (pk, json.dumps(pl))
            )
        conn.commit()
        msg = 'Datos iniciales cargados'
    else:
        msg = 'BD ya tenía datos, no se sobreescribió'

    cur.close()
    conn.close()
    return jsonify({'ok': True, 'message': msg})

# ─── STOCK ────────────────────────────────────────────────
@app.route('/api/stock', methods=['GET'])
def get_stock():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT data FROM stock ORDER BY (data->>'codigo') ASC;")
    rows = [r['data'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/stock/<item_id>', methods=['PUT'])
def update_stock(item_id):
    data = request.get_json()
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE stock SET data=%s, updated_at=NOW() WHERE id=%s",
        (json.dumps(data), item_id)
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ─── MOVIMIENTOS ──────────────────────────────────────────
@app.route('/api/movimientos', methods=['GET'])
def get_movimientos():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT data FROM movimientos ORDER BY (data->>'fecha') ASC;")
    rows = [r['data'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/movimientos', methods=['POST'])
def add_movimiento():
    data = request.get_json()
    if not data.get('id'):
        data['id'] = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO movimientos (id, data) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET data=%s",
        (data['id'], json.dumps(data), json.dumps(data))
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'id': data['id']})

# ─── INFORMES (merma baja) ────────────────────────────────
@app.route('/api/informes', methods=['GET'])
def get_informes():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT data FROM informes ORDER BY created_at DESC;")
    rows = [r['data'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/informes', methods=['POST'])
def add_informe():
    data = request.get_json()
    if not data.get('id'):
        data['id'] = f"INF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO informes (id, data) VALUES (%s, %s)",
        (data['id'], json.dumps(data))
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'id': data['id']})

# ─── PACKING LIST ─────────────────────────────────────────
@app.route('/api/packing', methods=['GET'])
def get_packing():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT data FROM packing_list ORDER BY (data->>'fecha_ing') ASC;")
    rows = [r['data'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/packing', methods=['POST'])
def add_packing():
    items = request.get_json()  # lista de items
    conn = get_db()
    cur  = conn.cursor()
    for i, item in enumerate(items):
        pk = item.get('id') or f"PL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}"
        item['id'] = pk
        cur.execute(
            "INSERT INTO packing_list (id, data) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET data=%s, updated_at=NOW()",
            (pk, json.dumps(item), json.dumps(item))
        )
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ─── HEALTH ──────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

# ─── START ───────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
