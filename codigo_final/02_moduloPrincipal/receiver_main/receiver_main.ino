#include <Arduino.h>
#include "communication.h"
#include "mqtt_client.h"
#include "rfid_reader.h"

// Tópicos MQTT
const char* topicVibration = "datos/vibracion";
const char* topicCurrent   = "datos/corriente";
const char* topicOperator  = "datos/operador";
const char* topicMicroParo = "datos/microparo";  // <<< AGREGADO

void setup() {
    Serial.begin(115200);
    delay(1000);

    startCom();
    initMQTT();
    initRFID();

    Serial.println("ESP32 Principal listo.");
}

void loop() {
    loopMQTT();

    // --- RFID ---
    uint64_t uidDecimal;
    if (checkForCard(uidDecimal)) {
        String payload = String(uidDecimal);
        publishMQTT(topicOperator, payload.c_str());
        Serial.println("Tarjeta detectada: " + payload);
        delay(800);
    }

    // --- Vibración ---
    if (newVibrationDataAvailable()) {
        float x = getVibrationX();
        float y = getVibrationY();
        float z = getVibrationZ();
        char payload[80];
        snprintf(payload, sizeof(payload), "ID:VIBRATION;X:%.2f,Y:%.2f,Z:%.2f", x, y, z);
        publishMQTT(topicVibration, payload);
        Serial.println(payload);
    }

    // --- Corriente ---
    if (newCurrentDataAvailable()) {
        float current = getCurrentValue();
        char payload[50];
        snprintf(payload, sizeof(payload), "ID:CURRENT;VALUE:%.2f", current);
        publishMQTT(topicCurrent, payload);
        Serial.println(payload);
    }

    // --- Microparo (botonera) ---
    if (newMicroParoAvailable()) {
        String msg = getMicroParoMsg();
        publishMQTT(topicMicroParo, msg.c_str());
        Serial.print("MicroParo publicado: ");
        Serial.println(msg);
    }

    delay(50);
}
