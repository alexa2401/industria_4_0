#ifndef RFID_READER_H
#define RFID_READER_H

#include <Arduino.h>

void initRFID();
bool checkForCard(uint64_t &uidDecimal);

#endif
