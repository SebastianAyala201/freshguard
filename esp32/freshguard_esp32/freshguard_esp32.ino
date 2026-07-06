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

int leerSensor(int pin) {
  long suma = 0;
  for (int i = 0; i < 10; i++) {
    suma += analogRead(pin);
    delay(10);
  }
  return suma / 10;
}

String calcularAlerta(int mq135, int mq3) {
  if (mq135 > 700 || mq3 > 700) return "CRITICO";
  if (mq135 > 450 || mq3 > 450) return "ADVERTENCIA";
  return "NORMAL";
}

float calcularIndiceFrescura(float temp, float hum, int mq135, int mq3) {
  float co2_norm    = constrain(map(mq135, 0, 4095, 0, 100), 0, 100);
  float etanol_norm = constrain(map(mq3,   0, 4095, 0, 100), 0, 100);
  float temp_pen    = constrain((temp - 25) * 5, 0, 100);
  float hum_pen     = constrain((hum  - 70) * 3, 0, 100);

  float indice = 100 - (
    co2_norm    * 0.35 +
    etanol_norm * 0.35 +
    temp_pen    * 0.15 +
    hum_pen     * 0.15
  );
  return constrain(indice, 0, 100);
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
  int mq135  = leerSensor(MQ135_PIN);
  int mq3    = leerSensor(MQ3_PIN);
  String alerta = calcularAlerta(mq135, mq3);
  float indice  = calcularIndiceFrescura(temp, hum, mq135, mq3);

  Serial.println("==================");
  Serial.print("Temperatura: "); Serial.println(temp);
  Serial.print("Humedad: ");     Serial.println(hum);
  Serial.print("MQ-135: ");      Serial.println(mq135);
  Serial.print("MQ-3: ");        Serial.println(mq3);
  Serial.print("Indice Frescura: "); Serial.println(indice);
  Serial.println("Alerta: " + alerta);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", apiKey);

    String json = "{";
    json += "\"temperatura\":"    + String(temp)   + ",";
    json += "\"humedad\":"        + String(hum)    + ",";
    json += "\"mq135\":"          + String(mq135)  + ",";
    json += "\"mq3\":"            + String(mq3)    + ",";
    json += "\"indice_frescura\":" + String(indice) + ",";
    json += "\"alerta\":\""       + alerta + "\"";
    json += "}";

    int httpCode = http.POST(json);
    Serial.print("Servidor: "); Serial.println(httpCode);
    http.end();
  }

  delay(3000);
}