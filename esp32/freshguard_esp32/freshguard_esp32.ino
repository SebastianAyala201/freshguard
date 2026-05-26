#include <DHT.h>
#include <WiFi.h>
#include <HTTPClient.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34
#define MQ137_PIN 35

const char* ssid     = "SEBAS";
const char* password = "MateSebas";
const char* serverURL = "http://192.168.1.38:5000/api/datos";
const char* apiKey    = "freshguard-2026-unmsm";

DHT dht(DHTPIN, DHTTYPE);

String calcularAlerta(int mq135, int mq137) {
  if (mq135 > 700 || mq137 > 700) return "CRITICO";
  if (mq135 > 450 || mq137 > 450) return "ADVERTENCIA";
  return "NORMAL";
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
  Serial.println("Calentando sensores...");
  delay(10000);
}

void loop() {
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  int mq135  = analogRead(MQ135_PIN);
  int mq137  = analogRead(MQ137_PIN);
  String alerta = calcularAlerta(mq135, mq137);

  Serial.println("==================");
  Serial.print("Temperatura: "); Serial.println(temp);
  Serial.print("Humedad: ");     Serial.println(hum);
  Serial.print("MQ-135: ");      Serial.println(mq135);
  Serial.print("MQ-137: ");      Serial.println(mq137);
  Serial.println("Alerta: " + alerta);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", apiKey);

    String json = "{";
    json += "\"temperatura\":" + String(temp) + ",";
    json += "\"humedad\":"     + String(hum)  + ",";
    json += "\"mq135\":"       + String(mq135) + ",";
    json += "\"mq137\":"       + String(mq137) + ",";
    json += "\"alerta\":\""    + alerta + "\"";
    json += "}";

    int httpCode = http.POST(json);
    Serial.print("Respuesta servidor: ");
    Serial.println(httpCode);
    http.end();
  }

  delay(3000);
}