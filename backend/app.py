from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict, deque
import statistics
import time

from config import (
    UMBRAL_CRITICO_MQ135, UMBRAL_ADVERTENCIA_MQ135,
    UMBRAL_CRITICO_MQ3, UMBRAL_ADVERTENCIA_MQ3,
    API_KEY, NODO_ID, NODO_LUGAR,
    RATE_LIMIT_MAX_PETICIONES, RATE_LIMIT_VENTANA_SEG,
    BLOQUEO_UMBRAL_RECHAZOS, BLOQUEO_DURACION_SEG,
    ZSCORE_UMBRAL, ZSCORE_MIN_LECTURAS
)

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
    "anomalia": False,
    "timestamp": "Sin datos aún",
    "nodo": NODO_ID,
    "lugar": NODO_LUGAR
}

nodos_activos = {}

# ═══════════════════════════════════════════════
# CIBERSEGURIDAD — Rate Limiting, Bloqueo automático y Log
# ═══════════════════════════════════════════════
peticiones_por_ip     = defaultdict(list)   # ip -> [timestamps de sus peticiones]
rechazos_consecutivos = defaultdict(int)    # ip -> nº de rechazos seguidos
ips_bloqueadas        = {}                  # ip -> timestamp en que se desbloquea
log_seguridad         = deque(maxlen=200)   # últimos 200 eventos de seguridad


def registrar_evento_seguridad(ip, motivo):
    """Guarda IP, timestamp y motivo de cada rechazo (Anti-Repudiation - STRIDE)."""
    evento = {
        "ip": ip,
        "timestamp": datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S"),
        "motivo": motivo
    }
    log_seguridad.append(evento)
    print(f"[SEGURIDAD] IP:{ip} | Motivo:{motivo} | {evento['timestamp']}")


def rate_limit_excedido(ip):
    """Máximo N peticiones por IP en una ventana de tiempo (Anti-DoS - STRIDE)."""
    ahora = time.time()
    peticiones_por_ip[ip] = [t for t in peticiones_por_ip[ip] if ahora - t < RATE_LIMIT_VENTANA_SEG]
    peticiones_por_ip[ip].append(ahora)
    return len(peticiones_por_ip[ip]) > RATE_LIMIT_MAX_PETICIONES


def ip_esta_bloqueada(ip):
    """Self-Protection: revisa si la IP sigue bloqueada automáticamente."""
    fin_bloqueo = ips_bloqueadas.get(ip)
    if fin_bloqueo is None:
        return False
    if time.time() > fin_bloqueo:
        del ips_bloqueadas[ip]        # el bloqueo expiró -> se autorestablece
        rechazos_consecutivos[ip] = 0
        return False
    return True


def registrar_rechazo_y_evaluar_bloqueo(ip, motivo):
    """Self-Protection: bloquea automáticamente IPs con demasiados rechazos seguidos."""
    registrar_evento_seguridad(ip, motivo)
    rechazos_consecutivos[ip] += 1
    if rechazos_consecutivos[ip] >= BLOQUEO_UMBRAL_RECHAZOS:
        ips_bloqueadas[ip] = time.time() + BLOQUEO_DURACION_SEG
        registrar_evento_seguridad(ip, f"IP BLOQUEADA automáticamente por {BLOQUEO_DURACION_SEG}s")


# ═══════════════════════════════════════════════
# LÓGICA DE NEGOCIO — Umbrales, Índice y Anomalías
# ═══════════════════════════════════════════════
def calcular_alerta(mq135, mq3):
    """Cada sensor mide una magnitud distinta, por eso usa su propio umbral."""
    if mq135 > UMBRAL_CRITICO_MQ135 or mq3 > UMBRAL_CRITICO_MQ3:
        return "CRITICO"
    if mq135 > UMBRAL_ADVERTENCIA_MQ135 or mq3 > UMBRAL_ADVERTENCIA_MQ3:
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


def detectar_anomalia_zscore(indice_actual):
    """Compara la lectura actual contra el historial reciente usando Z-score.
    Si se aleja demasiado del comportamiento normal, se marca como anómala."""
    historial = Lectura.query.order_by(Lectura.id.desc()).limit(50).all()
    if len(historial) < ZSCORE_MIN_LECTURAS:
        return False, None

    valores = [l.indice for l in historial]
    media = statistics.mean(valores)
    desviacion = statistics.pstdev(valores)

    if desviacion == 0:
        return False, 0.0

    z = (indice_actual - media) / desviacion
    return abs(z) > ZSCORE_UMBRAL, round(z, 2)


# ─── MIDDLEWARE ────────────────────────────────
@app.route('/api/datos', methods=['POST'])
def recibir_datos():
    global datos_actuales
    ip = request.remote_addr

    # 1) Self-Protection: ¿la IP está bloqueada por abuso previo?
    if ip_esta_bloqueada(ip):
        registrar_evento_seguridad(ip, "Petición rechazada - IP bloqueada")
        return jsonify({"error": "IP bloqueada temporalmente"}), 403

    # 2) Anti-DoS: ¿excede el límite de peticiones por minuto?
    if rate_limit_excedido(ip):
        registrar_rechazo_y_evaluar_bloqueo(ip, "Rate limit excedido (posible DoS)")
        return jsonify({"error": "Demasiadas peticiones, intenta más tarde"}), 429

    # 3) Autenticación por API Key
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        registrar_rechazo_y_evaluar_bloqueo(ip, "API Key inválida")
        return jsonify({"error": "No autorizado"}), 401

    # Petición legítima -> resetea el contador de rechazos de esa IP
    rechazos_consecutivos[ip] = 0

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
    anomalia, zscore = detectar_anomalia_zscore(indice)
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
        "anomalia":        anomalia,
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
        "anomalia":        anomalia,
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

    etiqueta_anomalia = " | ⚠️ ANOMALÍA" if anomalia else ""
    print(f"[{timestamp}] {nodo_id} | {alerta} | IF:{indice} | {etapa} | T:{temperatura}°C H:{humedad}%{etiqueta_anomalia}")
    return jsonify({
        "status": "ok",
        "alerta": alerta,
        "indice_frescura": indice,
        "anomalia": anomalia,
        "zscore": zscore
    }), 200


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


@app.route('/api/nodos', methods=['GET'])
def obtener_nodos():
    return jsonify(nodos_activos), 200


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


# Endpoint opcional: expone el log de seguridad para mostrarlo en vivo
# durante la presentación (no requiere tocar ningún template).
@app.route('/api/seguridad', methods=['GET'])
def obtener_log_seguridad():
    return jsonify(list(log_seguridad)), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
