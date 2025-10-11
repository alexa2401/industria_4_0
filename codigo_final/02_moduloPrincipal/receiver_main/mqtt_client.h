#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <Arduino.h>

void initMQTT();
void loopMQTT();
void publishMQTT(const char* topic, const char* payload);

#endif
