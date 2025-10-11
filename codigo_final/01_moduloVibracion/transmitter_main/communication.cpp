#include "communication.h"

// Dirección broadcast (no requiere emparejar una MAC específica)
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

void startCom() {
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al inicializar ESP-NOW");
    return;
  }
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Fallo al añadir peer");
  }
  Serial.println("Comunicación ESP-NOW iniciada");
}

void stopCom() {
  esp_now_deinit();
  Serial.println("Comunicación ESP-NOW detenida");
}

void sendMsg(uint8_t *data, size_t len) {
  esp_err_t result = esp_now_send(broadcastAddress, data, len);
  if (result == ESP_OK)
    Serial.println("Datos enviados correctamente");
  else
    Serial.println("Error al enviar datos");
}
