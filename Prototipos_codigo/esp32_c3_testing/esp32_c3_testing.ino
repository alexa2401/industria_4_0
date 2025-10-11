#include <WiFi.h>

const char* ssid = "ESP32-C3_AP";
const char* password = "12345678";  // mínimo 8 caracteres

void setup() {
  Serial.begin(115200);

  // Inicia en modo Access Point
  WiFi.softAP(ssid, password);

  Serial.println("Punto de acceso iniciado.");
  Serial.print("SSID: ");
  Serial.println(ssid);
  Serial.print("IP: ");
  Serial.println(WiFi.softAPIP());
}

void loop() {
  // No hace nada, solo mantiene el AP activo
}
