#include "communication.h"
#include "imu_sensor.h"

void setup() {
  Serial.begin(115200);
  initIMU();
  startCom();
}

void loop() {
  IMUData data = readIMU();
  sendMsg((uint8_t*)&data, sizeof(IMUData));
  delay(500);
}
