#include "communication.h"
#include <esp_now.h>
#include <WiFi.h>

// --- Variables para vibración ---
static float vibrationX = 0;
static float vibrationY = 0;
static float vibrationZ = 0;
static bool vibrationAvailable = false;

// --- Variables para corriente ---
static float currentValue = 0;
static bool currentAvailable = false;

// --- Variables para microparo (botonera) ---
static String microParoMsg = "";
static bool microParoAvailable = false;

// --- Callback para recepción ESP-NOW ---
void onDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len) {
    String msg = "";
    for (int i = 0; i < len; i++) msg += (char)data[i];

    // --- Vibración ---
    if (msg.startsWith("ID:VIBRATION")) {
        int xIndex = msg.indexOf("X:");
        int yIndex = msg.indexOf("Y:");
        int zIndex = msg.indexOf("Z:");

        if (xIndex != -1 && yIndex != -1 && zIndex != -1) {
            vibrationX = msg.substring(xIndex + 2, yIndex - 1).toFloat();
            vibrationY = msg.substring(yIndex + 2, zIndex - 1).toFloat();
            vibrationZ = msg.substring(zIndex + 2).toFloat();
            vibrationAvailable = true;
        }
    }

    // --- Corriente ---
    else if (msg.startsWith("ID:CURRENT")) {
        int vIndex = msg.indexOf("VALUE:");
        if (vIndex != -1) {
            currentValue = msg.substring(vIndex + 6).toFloat();
            currentAvailable = true;
        }
    }

    // --- Microparo (botonera) ---
    else if (msg.startsWith("ID:BUTTON")) {
        microParoMsg = msg;   // guardamos el mensaje tal cual llega
        microParoAvailable = true;
    }
}

void startCom() {
    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) {
        Serial.println("Error al iniciar ESP-NOW");
        return;
    }
    esp_now_register_recv_cb(onDataRecv);
    Serial.println("Receptor ESP-NOW iniciado");
}

// --- Vibración ---
bool newVibrationDataAvailable() { return vibrationAvailable; }
float getVibrationX() { vibrationAvailable = false; return vibrationX; }
float getVibrationY() { return vibrationY; }
float getVibrationZ() { return vibrationZ; }

// --- Corriente ---
bool newCurrentDataAvailable() { return currentAvailable; }
float getCurrentValue() { currentAvailable = false; return currentValue; }

// --- Microparo (botonera) ---
bool newMicroParoAvailable() { return microParoAvailable; }
String getMicroParoMsg() { microParoAvailable = false; return microParoMsg; }
