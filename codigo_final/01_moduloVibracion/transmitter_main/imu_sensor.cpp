#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include "imu_sensor.h"

// Pines del GY-61/ADXL335
const int xPin = D0;
const int yPin = D1;
const int zPin = D2;

// Referencias del ADC
const float VREF = 3.3;
const int ADC_RES = 4095;  // 12 bits

void initVibrationSensor() {
    WiFi.mode(WIFI_STA);
    if(esp_now_init() != ESP_OK){
        Serial.println("Error inicializando ESP-NOW");
        return;
    }

    esp_now_peer_info_t peer = {};
    memset(&peer, 0, sizeof(peer));
    memcpy(peer.peer_addr, "\xFF\xFF\xFF\xFF\xFF\xFF", 6); // Broadcast
    peer.channel = 0;
    peer.encrypt = false;
    esp_now_add_peer(&peer);

    Serial.println("Sensor de vibración GY-61 y ESP-NOW inicializados");
}

void sendVibrationData() {
    // Leer ADC
    int rawX = analogRead(xPin);
    int rawY = analogRead(yPin);
    int rawZ = analogRead(zPin);

    // Convertir a voltaje
    float ax = (rawX * VREF) / ADC_RES;
    float ay = (rawY * VREF) / ADC_RES;
    float az = (rawZ * VREF) / ADC_RES;

    // Construir payload
    char payload[80];
    snprintf(payload, sizeof(payload),
             "ID:VIBRATION;X:%.2f,Y:%.2f,Z:%.2f", ax, ay, az);

    // Enviar por ESP-NOW
    esp_err_t result = esp_now_send((uint8_t*)"\xFF\xFF\xFF\xFF\xFF\xFF",
                                    (uint8_t*)payload, strlen(payload)+1);
    if(result == ESP_OK) {
        Serial.println("Mensaje de vibración enviado");
    } else {
        Serial.println("Error enviando mensaje ESP-NOW");
    }
}
