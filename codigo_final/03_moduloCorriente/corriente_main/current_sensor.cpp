#include "current_sensor.h"
#include <WiFi.h>
#include <esp_now.h>

const int analogPin = A0;
const float VREF = 3.3;
const int ADC_RES = 4095;
const float OFFSET = VREF/2;
const float CURRENT_FACTOR = 300.0;
const float CLIP_MIN = 6.0;

float getCurrentRMS(int samples) {
    double sumSq = 0;
    for(int i=0;i<samples;i++){
        int adcValue = analogRead(analogPin);
        float voltage = (adcValue*VREF)/ADC_RES;
        float centered = voltage - OFFSET;
        sumSq += centered*centered;
        delayMicroseconds(200);
    }
    float meanSq = sumSq/samples;
    float vRMS = sqrt(meanSq);
    float currentRMS = vRMS*CURRENT_FACTOR;
    if(currentRMS<CLIP_MIN) currentRMS=0;
    else currentRMS-=CLIP_MIN;
    return currentRMS;
}

void initCurrentSensor() {
    WiFi.mode(WIFI_STA);
    if(esp_now_init() != ESP_OK){
        Serial.println("Error ESP-NOW");
        return;
    }
    esp_now_peer_info_t peer={};
    memset(&peer,0,sizeof(peer));
    memcpy(peer.peer_addr,"\xFF\xFF\xFF\xFF\xFF\xFF",6);
    peer.channel=0;
    peer.encrypt=false;
    esp_now_add_peer(&peer);
}

void sendCurrentData() {
    float current = getCurrentRMS(1000);
    char payload[30];
    snprintf(payload,sizeof(payload),"ID:CURRENT;VALUE:%.3f",current);
    esp_now_send((uint8_t*)"\xFF\xFF\xFF\xFF\xFF\xFF",(uint8_t*)payload,strlen(payload)+1);
    Serial.print("Mensaje de corriente enviado: ");
    Serial.println(current,3);
}
