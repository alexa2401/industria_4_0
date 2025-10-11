#include "communication.h"
#include "mqtt_client.h"

void onRecv(const esp_now_recv_info *info, const uint8_t *data, int len) {
  receiveMsg(data, len);
}

void startCom() {
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al iniciar ESP-NOW");
    return;
  }
  esp_now_register_recv_cb(onRecv);
  Serial.println("Receptor ESP-NOW iniciado correctamente");
}

void stopCom() {
  esp_now_deinit();
  Serial.println("Comunicación ESP-NOW detenida");
}

void receiveMsg(const uint8_t *data, int len) {
  if (len != sizeof(int) * 3) {
    Serial.print("Paquete inesperado (len = ");
    Serial.print(len);
    Serial.println(")");
    return;
  }

  int *values = (int*)data;

  Serial.print("IMU -> X:");
  Serial.print(values[0]);
  Serial.print(" | Y:");
  Serial.print(values[1]);
  Serial.print(" | Z:");
  Serial.println(values[2]);

  // Construir mensaje como string plano
  String payload = "X:" + String(values[0]) +
                   ",Y:" + String(values[1]) +
                   ",Z:" + String(values[2]);

  // Publicar en el tópico MQTT
  publishMQTT("datos/vibraciones", payload.c_str());
}

void sendMsg(uint8_t *data, size_t len) {
  // No se usa en el receptor
}

