# FreshGuard

FreshGuard es un sistema IoT para monitoreo de frescura de frutas basado en ESP32, sensores de temperatura, humedad, MQ-135 y MQ-3, y un backend web en Flask que registra lecturas, calcula el índice de frescura y muestra paneles de visualización.

El proyecto incluye tres partes principales:

- Backend web en Flask con SQLite y vistas HTML.
- Sketch para ESP32 que captura sensores y envía datos al servidor.
- Simulador de nodos para generar lecturas de prueba desde varios puntos de monitoreo.

## Características

- Recepción de datos por API REST con autenticación por `X-API-Key`.
- Cálculo del índice de frescura y de la etapa de madurez.
- Alertas por sensor con umbrales separados para MQ-135 y MQ-3.
- Detección simple de anomalías usando Z-score sobre el historial reciente.
- Rate limiting y bloqueo temporal de IPs ante abuso de peticiones.
- Persistencia de lecturas en SQLite.
- Paneles web para inicio, dashboard, arquitectura, literatura y vista smart city.

## Estructura del proyecto

```text
freshguard/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── simulador_nodos.py
│   ├── static/
│   └── templates/
└── esp32/
    └── freshguard_esp32/
        └── freshguard_esp32.ino
```

## Requisitos

- Python 3.10 o superior.
- pip.
- Arduino IDE o PlatformIO para cargar el sketch en ESP32.
- Un dispositivo ESP32 con sensores compatibles si vas a usar hardware real.

## Instalación del backend

1. Entra a la carpeta `backend`.
2. Crea y activa un entorno virtual.
3. Instala las dependencias.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar el servidor

Desde la carpeta `backend`:

```bash
python app.py
```

El servidor queda disponible en `http://localhost:5000`.

Al iniciar por primera vez se crea automáticamente la base de datos `freshguard.db`.

## Vistas web

- `/` - Inicio con estado actual e historial reciente.
- `/dashboard` - Panel principal de monitoreo.
- `/smartcity` - Vista de nodos activos.
- `/arquitectura` - Diagrama de arquitectura.
- `/literatura` - Sección de referencia documental.

## API

### Enviar datos

`POST /api/datos`

Encabezado requerido:

```http
X-API-Key: freshguard-2026-unmsm
Content-Type: application/json
```

Ejemplo de cuerpo:

```json
{
  "temperatura": 24.5,
  "humedad": 78.2,
  "mq135": 620,
  "mq3": 410,
  "nodo": "ESP32-FRESHGUARD-01",
  "lugar": "Laboratorio UNMSM"
}
```

### Consultas útiles

- `GET /api/estado` - Devuelve el estado actual del nodo.
- `GET /api/nodos` - Lista los nodos activos detectados.
- `GET /api/historial` - Retorna las últimas 50 lecturas almacenadas.
- `GET /api/seguridad` - Expone el log reciente de eventos de seguridad.

## Simulador de nodos

El archivo `backend/simulador_nodos.py` envía lecturas aleatorias a un servidor remoto ya configurado en el script. Sirve para probar el flujo con varios nodos sin usar hardware real.

Para ejecutarlo:

```bash
cd backend
python simulador_nodos.py
```

## ESP32

El sketch está en `esp32/freshguard_esp32/freshguard_esp32.ino`.

Antes de cargarlo en tu placa verifica estas variables:

- `ssid`
- `password`
- `serverURL`
- `apiKey`

El firmware lee:

- DHT22 para temperatura y humedad.
- MQ-135 para gases asociados a deterioro.
- MQ-3 para etanol.

Luego envía los datos por HTTP al backend usando la API Key configurada.

## Configuración

Los umbrales y parámetros globales están en `backend/config.py`.

Ahí puedes ajustar:

- Umbrales de alerta para MQ-135 y MQ-3.
- Identidad del nodo.
- Límite de peticiones por IP.
- Duración del bloqueo automático.
- Parámetros del detector de anomalías.

## Notas

- La API Key está compartida entre el backend, el sketch y el simulador. Si la cambias, actualiza los tres lugares.
- La aplicación usa SQLite, así que no requiere una base de datos externa.
- Si despliegas en otro entorno, revisa la URL del servidor en el ESP32 y en el simulador.

## Licencia

No se ha definido una licencia en este repositorio.