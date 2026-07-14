#include <DHT.h>
#include <WiFi.h>
#include <HTTPClient.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34
#define MQ3_PIN 32

const char* ssid      = "SEBAS";
const char* password  = "MateSebas";
const char* serverURL = "https://freshguard-0ibl.onrender.com/api/datos";
const char* apiKey    = "freshguard-2026-unmsm";

DHT dht(DHTPIN, DHTTYPE);

int fallosConsecutivos = 0;
const int MAX_FALLOS_ANTES_DE_REINICIAR = 8;

int leerSensor(int pin) {
  long suma = 0;
  for (int i = 0; i < 10; i++) {
    suma += analogRead(pin);
    delay(10);
  }
  return suma / 10;
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  WiFi.begin(ssid, password);
  Serial.print("Conectando WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n¡Conectado!");
  Serial.println("Calentando sensores 30 seg...");
  delay(30000);
  Serial.println("¡Listo!");
}

void loop() {
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  // Proteccion: el DHT22 a veces falla una lectura (timing, cable, ruido).
  // Si eso pasa, nos saltamos este ciclo en vez de mandar un JSON invalido.
  if (isnan(temp) || isnan(hum)) {
    Serial.println("⚠️ Lectura DHT22 fallida, reintentando en el siguiente ciclo...");
    delay(3000);
    return;
  }

  int mq135 = leerSensor(MQ135_PIN);
  int mq3   = leerSensor(MQ3_PIN);

  Serial.println("==================");
  Serial.print("Temperatura: "); Serial.println(temp);
  Serial.print("Humedad: ");     Serial.println(hum);
  Serial.print("MQ-135: ");      Serial.println(mq135);
  Serial.print("MQ-3: ");        Serial.println(mq3);

  // Self-Healing a nivel de red: si el WiFi se cayo, reintenta reconectar
  // antes de intentar mandar datos.
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi desconectado, reconectando...");
    WiFi.reconnect();
    delay(2000);
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.setConnectTimeout(10000);   // 10s para conectar (antes ~5s por defecto)
    http.setTimeout(10000);          // 10s para recibir respuesta
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", apiKey);

    // El indice y la alerta ya no se calculan aqui: el backend los recalcula
    // con sus propios umbrales (config.py), asi que solo mandamos los datos
    // crudos de los sensores. Menos codigo, menos que explicar.
    String json = "{";
    json += "\"temperatura\":" + String(temp) + ",";
    json += "\"humedad\":"     + String(hum)  + ",";
    json += "\"mq135\":"       + String(mq135) + ",";
    json += "\"mq3\":"         + String(mq3);
    json += "}";

    int httpCode = http.POST(json);
    Serial.print("Servidor: "); Serial.print(httpCode);
    Serial.print(" | Heap libre: "); Serial.println(ESP.getFreeHeap());
    http.end();

    // Self-Healing: si fallan varias peticiones seguidas (probable
    // fragmentacion de memoria tras muchas conexiones HTTPS), el ESP32
    // se reinicia solo. Un reinicio limpia la memoria y reconecta desde
    // cero, sin necesitar intervencion humana.
    if (httpCode > 0) {
      fallosConsecutivos = 0;
    } else {
      fallosConsecutivos++;
      Serial.print("Fallos consecutivos: "); Serial.println(fallosConsecutivos);
      if (fallosConsecutivos >= MAX_FALLOS_ANTES_DE_REINICIAR) {
        Serial.println("⚠️ Demasiados fallos seguidos, reiniciando ESP32...");
        delay(500);
        ESP.restart();
      }
    }
  }

  delay(3000);
}
