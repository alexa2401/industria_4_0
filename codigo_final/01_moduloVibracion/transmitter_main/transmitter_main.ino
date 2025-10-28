#include "imu_sensor.h"

void setup() {
    Serial.begin(115200);
    initVibrationSensor();
}

void loop() {
    sendVibrationData();
    delay(500);  // enviar cada 500 ms
}
