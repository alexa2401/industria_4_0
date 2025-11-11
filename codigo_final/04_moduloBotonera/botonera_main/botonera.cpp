#include "botonera.h"
#include <WiFi.h>
#include <esp_now.h>

// Pines
const int btnPins[3] = {D6, D5, D7};
const int ledPins[3] = {D4, D3, D2};

// Estados de LEDs
bool ledStates[3] = {false, false, false};
bool lastBtnState[3] = {HIGH, HIGH, HIGH};

void sendMicroParo(const char* msg) {
    esp_now_send((uint8_t*)"\xFF\xFF\xFF\xFF\xFF\xFF", (uint8_t*)msg, strlen(msg) + 1);
    Serial.print("Enviado via ESP-NOW: ");
    Serial.println(msg);
}

void initBotonera() {
    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK){
        Serial.println("Error ESP-NOW");
        return;
    }

    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, "\xFF\xFF\xFF\xFF\xFF\xFF", 6);
    peer.channel = 0;
    peer.encrypt = false;
    esp_now_add_peer(&peer);

    for(int i = 0; i < 3; i++){
        pinMode(btnPins[i], INPUT_PULLUP);
        pinMode(ledPins[i], OUTPUT);
        digitalWrite(ledPins[i], LOW);
    }
}

void updateBotonera() {
    static bool stableState[3] = {HIGH, HIGH, HIGH};   // Estado limpio (sin rebote)
    static bool lastRawState[3] = {HIGH, HIGH, HIGH};  // Última lectura cruda
    static unsigned long lastDebounceTime[3] = {0,0,0};
    const unsigned long debounceDelay = 50;

    for(int i = 0; i < 3; i++) {

        bool rawReading = digitalRead(btnPins[i]);

        // Si la lectura cruda cambió, reiniciar debounce
        if(rawReading != lastRawState[i]) {
            lastDebounceTime[i] = millis();
        }

        // Si ya pasó el debounceDelay, podemos actualizar estado estable
        if((millis() - lastDebounceTime[i]) > debounceDelay) {
            
            // Detectar flanco descendente estable
            if(stableState[i] == HIGH && rawReading == LOW) {

                // Toggle seguro del LED
                ledStates[i] = !ledStates[i];
                digitalWrite(ledPins[i], ledStates[i] ? HIGH : LOW);

                // Crear mensaje
                char microParoMsg[40];
                snprintf(microParoMsg, sizeof(microParoMsg),
                        "ID:BUTTON;ESTADO:%s;MID:%d",
                        ledStates[i] ? "verdadero" : "falso",
                        i + 1);

                sendMicroParo(microParoMsg);
            }

            // Actualizar estado estable
            stableState[i] = rawReading;
        }

        // Guardar lectura cruda para la próxima vuelta
        lastRawState[i] = rawReading;
    }
}

