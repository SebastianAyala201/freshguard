# FreshGuard - Configuración general

# ═══════════════════════════════════════════════
# Umbrales del sistema — SEPARADOS POR SENSOR
# MQ-135 (CO2/gases) y MQ-3 (etanol) miden magnitudes distintas
# y operan en rangos distintos (ver Tabla 8 del informe:
# MQ-135 se mueve entre ~500-600 ADC, MQ-3 entre ~1600-2300 ADC).
# Compartir un solo umbral hacía que el MQ-135 casi nunca
# pudiera disparar una alerta por sí mismo.
# ═══════════════════════════════════════════════
UMBRAL_CRITICO_MQ135     = 1500
UMBRAL_ADVERTENCIA_MQ135 = 900

UMBRAL_CRITICO_MQ3       = 3500
UMBRAL_ADVERTENCIA_MQ3   = 2000

TEMP_BASE = 18   # FAO recomendación frutas tropicales
HUM_BASE  = 85   # FAO recomendación conservación

# API Key de seguridad
API_KEY = "freshguard-2026-unmsm"

# Información del nodo
NODO_ID    = "ESP32-FRESHGUARD-01"
NODO_LUGAR = "Laboratorio UNMSM"

# ═══════════════════════════════════════════════
# Ciberseguridad — Rate Limiting (Anti-DoS, STRIDE)
# Calculado con margen sobre el tráfico legítimo esperado:
# ESP32 real (~20 peticiones/min) + simulador de 5 nodos (~20/min)
# ≈ 40/min si corren desde la misma IP. Se deja amplio margen
# porque un ataque DoS real manda cientos de peticiones/min,
# no ~40 — el límite protege sin interferir con la demo.
# ═══════════════════════════════════════════════
RATE_LIMIT_MAX_PETICIONES = 100  # peticiones máximas permitidas...
RATE_LIMIT_VENTANA_SEG    = 60   # ...por cada 60 segundos, por IP

# ═══════════════════════════════════════════════
# Autonomic Computing — Self-Protection
# ═══════════════════════════════════════════════
BLOQUEO_UMBRAL_RECHAZOS = 5     # rechazos seguidos antes de bloquear la IP
BLOQUEO_DURACION_SEG    = 300   # duración del bloqueo automático (5 minutos)

# ═══════════════════════════════════════════════
# Data Science — Detección de anomalías (Z-score)
# ═══════════════════════════════════════════════
ZSCORE_UMBRAL       = 2.5   # desviaciones estándar para marcar una anomalía
ZSCORE_MIN_LECTURAS = 10    # mínimo de lecturas históricas para calcular
