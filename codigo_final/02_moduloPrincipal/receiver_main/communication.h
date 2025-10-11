#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

void startCom();
void stopCom();
void receiveMsg(const uint8_t *data, int len);
void sendMsg(uint8_t *data, size_t len);

#endif
