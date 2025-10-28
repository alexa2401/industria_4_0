#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>

// Inicialización
void startCom();
void stopCom();

// --- Vibración ---
bool newVibrationDataAvailable();
float getVibrationX();
float getVibrationY();
float getVibrationZ();

// --- Corriente ---
bool newCurrentDataAvailable();
float getCurrentValue();

#endif
