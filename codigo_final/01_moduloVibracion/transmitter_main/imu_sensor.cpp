#include "imu_sensor.h"

const int xPin = D0;
const int yPin = D1;
const int zPin = D2;

void initIMU() {
  pinMode(xPin, INPUT);
  pinMode(yPin, INPUT);
  pinMode(zPin, INPUT);
}

IMUData readIMU() {
  IMUData data;
  data.x = analogRead(xPin);
  data.y = analogRead(yPin);
  data.z = analogRead(zPin);
  return data;
}
