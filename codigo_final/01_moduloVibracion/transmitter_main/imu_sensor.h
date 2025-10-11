#ifndef IMU_SENSOR_H
#define IMU_SENSOR_H

#include <Arduino.h>

struct IMUData {
  int x;
  int y;
  int z;
};

void initIMU();
IMUData readIMU();

#endif
