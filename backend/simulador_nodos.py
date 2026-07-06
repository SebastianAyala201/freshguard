import requests
import random
import time
from datetime import datetime

API_KEY = "freshguard-2026-unmsm"
SERVER  = "https://freshguard-0ibl.onrender.com/api/datos"

nodos = [
    {
        "nodo":  "ESP32-FRESHGUARD-02",
        "lugar": "Mercado La Parada - La Victoria"
    },
    {
        "nodo":  "ESP32-FRESHGUARD-03",
        "lugar": "Mercado Caqueta - Rimac"
    },
    {
        "nodo":  "ESP32-FRESHGUARD-04",
        "lugar": "Mercado Unicachi - SJL"
    },
    {
        "nodo":  "ESP32-FRESHGUARD-05",
        "lugar": "Mercado Condevilla - SMP"
    },
    {
        "nodo":  "ESP32-FRESHGUARD-06",
        "lugar": "Mercado Lurin - Lima Sur"
    },
]

def simular_nodo(nodo):
    datos = {
        "temperatura": round(random.uniform(18, 32), 1),
        "humedad":     round(random.uniform(60, 90), 1),
        "mq135":       random.randint(100, 800),
        "mq3":         random.randint(200, 1200),
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
        print(f"Error {nodo['lugar']}: {e}")

print("FreshGuard — Simulador Smart City Lima")
print("Nodos: La Parada, Caqueta, Unicachi, Condevilla, Lurin")
print("=" * 50)

while True:
    for nodo in nodos:
        simular_nodo(nodo)
        time.sleep(2)
    time.sleep(5)