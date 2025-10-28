#include "current_sensor.h"

void setup() {
    Serial.begin(115200);
    initCurrentSensor();
}

void loop() {
    sendCurrentData();
    delay(500);
}
