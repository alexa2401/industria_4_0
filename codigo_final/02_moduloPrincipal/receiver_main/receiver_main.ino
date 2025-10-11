#include "communication.h"
#include "mqtt_client.h"
#include "rfid_reader.h"

void setup() {
  Serial.begin(115200);
  delay(1000);

  startCom();    // Inicializa ESP-NOW
  initMQTT();    // Inicializa WiFi + MQTT
  initRFID();    // Inicializa lector RC522
}

void loop() {
  // Mantener MQTT vivo
  loopMQTT();

  // Revisa si hay tarjeta; si la hay, publica UID decimal en el topic datos/operador
  uint64_t uidDecimal;
  if (checkForCard(uidDecimal)) {
    // Construir payload como string plano con el UID decimal
    String payload = String(uidDecimal);
    publishMQTT("datos/operador", payload.c_str());

    // Mostrar en serial para debug
    Serial.print("Tarjeta detectada. UID decimal: ");
    Serial.println(payload);

    // Espera anti-rebote para evitar lecturas múltiples de la misma tarjeta
    delay(800);
  }

  delay(50);
}
