from flask import Flask, request, jsonify, render_template
from datetime import datetime
from zoneinfo import ZoneInfo
from config import UMBRAL_CRITICO, UMBRAL_ADVERTENCIA, API_KEY, NODO_ID, NODO_LUGAR

app = Flask(__name__)

# Almacena historial de lecturas
historial = []
datos_actuales = {
    "temperatura": 0,
    "humedad": 0,
    "mq135": 0,
    "mq3": 0,
    "indice_frescura": 100,
    "alerta": "SIN DATOS",
    "timestamp": "Sin datos aún",
    "nodo": NODO_ID,
    "lugar": NODO_LUGAR
}

def calcular_alerta(mq135, mq3):
    if mq135 > UMBRAL_CRITICO or mq3 > UMBRAL_CRITICO:
        return "CRITICO"
    if mq135 > UMBRAL_ADVERTENCIA or mq3 > UMBRAL_ADVERTENCIA:
        return "ADVERTENCIA"
    return "NORMAL"

def calcular_indice(temperatura, humedad, mq135, mq3):
    co2_norm    = min((mq135 / 4095) * 100, 100)
    etanol_norm = min((mq3   / 4095) * 100, 100)
    temp_pen    = max((temperatura - 25) * 5, 0)
    hum_pen     = max((humedad - 70) * 3, 0)

    indice = 100 - (
        co2_norm    * 0.35 +
        etanol_norm * 0.35 +
        temp_pen    * 0.15 +
        hum_pen     * 0.15
    )
    return round(max(min(indice, 100), 0), 1)

def etapa_madurez(indice):
    if indice >= 75: return "🟢 Verde / Fresco"
    if indice >= 50: return "🟡 Maduro"
    if indice >= 25: return "🟠 Sobremaduro"
    return "🔴 Podrido"

# ─── MIDDLEWARE / CAPA DE RED ──────────────────
@app.route('/api/datos', methods=['POST'])
def recibir_datos():
    global datos_actuales

    # Ciberseguridad: validar API Key
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
    indice      = body.get("indice_frescura") or calcular_indice(temperatura, humedad, mq135, mq3)
    alerta      = calcular_alerta(mq135, mq3)
    etapa       = etapa_madurez(indice)

    datos_actuales = {
        "temperatura":     temperatura,
        "humedad":         humedad,
        "mq135":           mq135,
        "mq3":             mq3,
        "indice_frescura": indice,
        "etapa":           etapa,
        "alerta":          alerta,
        "timestamp":       datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S"),
        "nodo":            NODO_ID,
        "lugar":           NODO_LUGAR
    }

    historial.append(datos_actuales.copy())
    if len(historial) > 50:
        historial.pop(0)

    print(f"[{datos_actuales['timestamp']}] {alerta} | IF:{indice} | {etapa} | T:{temperatura}°C H:{humedad}% MQ135:{mq135} MQ3:{mq3}")
    return jsonify({"status": "ok", "alerta": alerta, "indice_frescura": indice}), 200

# ─── CAPA DE APLICACIÓN ────────────────────────
@app.route('/')
def dashboard():
    return render_template('dashboard.html',
                         datos=datos_actuales,
                         historial=historial[-10:])

@app.route('/api/estado', methods=['GET'])
def obtener_estado():
    return jsonify(datos_actuales), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)