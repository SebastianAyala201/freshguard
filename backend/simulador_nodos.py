import requests
import random
import time
from datetime import datetime

API_KEY = "freshguard-2026-unmsm"
SERVER  = "https://freshguard-0ibl.onrender.com/api/datos"

nodos = [
    {"nodo": "ESP32-FRESHGUARD-02", "lugar": "Mercado Central Lima"},
    {"nodo": "ESP32-FRESHGUARD-03", "lugar": "Mercado Mayorista Lima"},
    {"nodo": "ESP32-FRESHGUARD-04", "lugar": "Centro Distribución Norte"},
]

def simular_nodo(nodo):
    datos = {
        "temperatura": round(random.uniform(24, 32), 1),
        "humedad":     round(random.uniform(60, 85), 1),
        "mq135":       random.randint(100, 800),
        "mq3":         random.randint(200, 1500),
        "nodo":        nodo["nodo"],
        "lugar":       nodo["lugar"]
    }
    try:
        r = requests.post(
            SERVER,
            json=datos,
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {nodo['lugar']} → {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

print("Iniciando simulación de nodos Smart City...")
while True:
    for nodo in nodos:
        simular_nodo(nodo)
        time.sleep(2)
    time.sleep(5)