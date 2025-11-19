#include "current_sensor.h"
#include <WiFi.h>
#include <esp_now.h>

const int analogPin = A0;

void initCurrentSensor() {
    WiFi.mode(WIFI_STA);

    if (esp_now_init() != ESP_OK) {
        Serial.println("Error inicializando ESP-NOW");
        return;
    }

    // Broadcast
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, "\xFF\xFF\xFF\xFF\xFF\xFF", 6);
    peer.channel = 0;
    peer.encrypt = false;

    if (esp_now_add_peer(&peer) != ESP_OK) {
        Serial.println("Error añadiendo peer");
        return;
    }
}

void sendCurrentData() {
    int adcValue = analogRead(analogPin);

    char payload[30];
    snprintf(payload, sizeof(payload), "ID:CURRENT;VALUE:%d", adcValue);

    esp_now_send((uint8_t*)"\xFF\xFF\xFF\xFF\xFF\xFF", (uint8_t*)payload, strlen(payload) + 1);

    Serial.print("ADC enviado: ");
    Serial.println(adcValue);
}
