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
    "mq137": 0,
    "alerta": "SIN DATOS",
    "timestamp": "Sin datos aún",
    "nodo": NODO_ID,
    "lugar": NODO_LUGAR
}

def calcular_alerta(mq135, mq137):
    if mq135 > UMBRAL_CRITICO or mq137 > UMBRAL_CRITICO:
        return "CRITICO"
    if mq135 > UMBRAL_ADVERTENCIA or mq137 > UMBRAL_ADVERTENCIA:
        return "ADVERTENCIA"
    return "NORMAL"

# ─── CAPA DE RED ───────────────────────────────
# Endpoint que recibe datos del ESP32 via HTTP POST
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

    mq135 = body.get("mq135", 0)
    mq137 = body.get("mq137", 0)
    alerta = calcular_alerta(mq135, mq137)

    datos_actuales = {
        "temperatura": body.get("temperatura", 0),
        "humedad":     body.get("humedad", 0),
        "mq135":       mq135,
        "mq137":       mq137,
        "alerta":      alerta,
        "timestamp": datetime.now(
                        ZoneInfo("America/Lima")
                    ).strftime("%Y-%m-%d %H:%M:%S"),
        "nodo":        NODO_ID,
        "lugar":       NODO_LUGAR
    }

    # Guardar en historial (máximo 50 lecturas)
    historial.append(datos_actuales.copy())
    if len(historial) > 50:
        historial.pop(0)

    print(f"[{datos_actuales['timestamp']}] {alerta} - T:{datos_actuales['temperatura']}°C H:{datos_actuales['humedad']}% MQ135:{mq135} MQ137:{mq137}")
    return jsonify({"status": "ok", "alerta": alerta}), 200

# ─── CAPA DE APLICACIÓN ────────────────────────
# Dashboard web
@app.route('/')
def dashboard():
    return render_template('dashboard.html', 
                         datos=datos_actuales,
                         historial=historial[-10:])

# API para obtener datos en JSON
@app.route('/api/estado', methods=['GET'])
def obtener_estado():
    return jsonify(datos_actuales), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)