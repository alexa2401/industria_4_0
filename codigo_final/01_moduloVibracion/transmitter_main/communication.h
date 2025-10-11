#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>

void startCom();
void stopCom();
void sendMsg(uint8_t *data, size_t len);

#endif
