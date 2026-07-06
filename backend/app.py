from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from zoneinfo import ZoneInfo
from config import UMBRAL_CRITICO, UMBRAL_ADVERTENCIA, API_KEY, NODO_ID, NODO_LUGAR

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freshguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Lectura(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.String(30))
    temperatura = db.Column(db.Float)
    humedad     = db.Column(db.Float)
    mq135       = db.Column(db.Integer)
    mq3         = db.Column(db.Integer)
    indice      = db.Column(db.Float)
    etapa       = db.Column(db.String(30))
    alerta      = db.Column(db.String(20))
    nodo        = db.Column(db.String(30))
    lugar       = db.Column(db.String(50))

datos_actuales = {
    "temperatura": 0,
    "humedad": 0,
    "mq135": 0,
    "mq3": 0,
    "indice_frescura": 100,
    "etapa": "Sin datos",
    "alerta": "SIN DATOS",
    "timestamp": "Sin datos aún",
    "nodo": NODO_ID,
    "lugar": NODO_LUGAR
}

nodos_activos = {}

def calcular_alerta(mq135, mq3):
    if mq135 > UMBRAL_CRITICO or mq3 > UMBRAL_CRITICO:
        return "CRITICO"
    if mq135 > UMBRAL_ADVERTENCIA or mq3 > UMBRAL_ADVERTENCIA:
        return "ADVERTENCIA"
    return "NORMAL"

def calcular_indice(temperatura, humedad, mq135, mq3):
    co2_norm    = min((mq135 / 4095) * 100, 100)
    etanol_norm = min((mq3   / 4095) * 100, 100)
    temp_pen    = max((temperatura - 18) * 5, 0)
    hum_pen     = max((85 - humedad) * 2, 0)
    indice = 100 - (
        co2_norm    * 0.30 +
        etanol_norm * 0.40 +
        temp_pen    * 0.15 +
        hum_pen     * 0.15
    )
    return round(max(min(indice, 100), 0), 1)

def etapa_madurez(indice):
    if indice >= 75: return "🟢 Verde / Fresco"
    if indice >= 50: return "🟡 Maduro"
    if indice >= 25: return "🟠 Sobremaduro"
    return "🔴 Podrido"

# ─── MIDDLEWARE ────────────────────────────────
@app.route('/api/datos', methods=['POST'])
def recibir_datos():
    global datos_actuales

    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        print(f"[SEGURIDAD] Acceso rechazado - API Key inválida")
        return jsonify({"error": "No autorizado"}), 401

    body = request.get_json()
    if not body:
        return jsonify({"error": "Datos inválidos"}), 400

    mq135       = body.get("mq135", 0)
    mq3         = body.get("mq3", 0)
    temperatura = body.get("temperatura", 0)
    humedad     = body.get("humedad", 0)
    indice      = calcular_indice(temperatura, humedad, mq135, mq3)
    alerta      = calcular_alerta(mq135, mq3)
    etapa       = etapa_madurez(indice)
    timestamp   = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    nodo_id     = body.get("nodo", NODO_ID)
    lugar       = body.get("lugar", NODO_LUGAR)

    nodos_activos[nodo_id] = {
        "temperatura":     temperatura,
        "humedad":         humedad,
        "mq135":           mq135,
        "mq3":             mq3,
        "indice_frescura": indice,
        "etapa":           etapa,
        "alerta":          alerta,
        "timestamp":       timestamp,
        "lugar":           lugar
    }

    datos_actuales = {
        "temperatura":     temperatura,
        "humedad":         humedad,
        "mq135":           mq135,
        "mq3":             mq3,
        "indice_frescura": indice,
        "etapa":           etapa,
        "alerta":          alerta,
        "timestamp":       timestamp,
        "nodo":            nodo_id,
        "lugar":           lugar
    }

    lectura = Lectura(
        timestamp   = timestamp,
        temperatura = temperatura,
        humedad     = humedad,
        mq135       = mq135,
        mq3         = mq3,
        indice      = indice,
        etapa       = etapa,
        alerta      = alerta,
        nodo        = nodo_id,
        lugar       = lugar
    )
    db.session.add(lectura)
    db.session.commit()

    print(f"[{timestamp}] {nodo_id} | {alerta} | IF:{indice} | {etapa} | T:{temperatura}°C H:{humedad}%")
    return jsonify({"status": "ok", "alerta": alerta, "indice_frescura": indice}), 200

# ─── CAPA DE APLICACIÓN ────────────────────────
@app.route('/')
def index():
    lecturas = Lectura.query.order_by(Lectura.id.desc()).limit(10).all()
    historial = [{
        "timestamp":       l.timestamp,
        "temperatura":     l.temperatura,
        "humedad":         l.humedad,
        "mq135":           l.mq135,
        "mq3":             l.mq3,
        "indice_frescura": l.indice,
        "etapa":           l.etapa,
        "alerta":          l.alerta
    } for l in lecturas]
    return render_template('index.html',
                         datos=datos_actuales,
                         historial=historial,
                         nodos=nodos_activos)

@app.route('/dashboard')
def dashboard():
    lecturas = Lectura.query.order_by(Lectura.id.desc()).limit(10).all()
    historial = [{
        "timestamp":       l.timestamp,
        "temperatura":     l.temperatura,
        "humedad":         l.humedad,
        "mq135":           l.mq135,
        "mq3":             l.mq3,
        "indice_frescura": l.indice,
        "etapa":           l.etapa,
        "alerta":          l.alerta
    } for l in lecturas]
    return render_template('dashboard.html',
                         datos=datos_actuales,
                         historial=historial,
                         nodos=nodos_activos)

@app.route('/smartcity')
def smartcity():
    return render_template('smartcity.html',
                         nodos=nodos_activos)

@app.route('/arquitectura')
def arquitectura():
    return render_template('arquitectura.html')

@app.route('/literatura')
def literatura():
    return render_template('literatura.html')

@app.route('/api/estado', methods=['GET'])
def obtener_estado():
    return jsonify(datos_actuales), 200

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    lecturas = Lectura.query.order_by(Lectura.id.desc()).limit(50).all()
    return jsonify([{
        "timestamp":   l.timestamp,
        "temperatura": l.temperatura,
        "humedad":     l.humedad,
        "mq135":       l.mq135,
        "mq3":         l.mq3,
        "indice":      l.indice,
        "etapa":       l.etapa,
        "alerta":      l.alerta
    } for l in lecturas]), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)