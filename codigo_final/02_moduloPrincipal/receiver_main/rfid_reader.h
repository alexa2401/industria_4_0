#ifndef RFID_READER_H
#define RFID_READER_H

#include <Arduino.h>
#include <MFRC522.h>

void initRFID();
bool checkForCard(uint64_t &uidDecimal); // retorna true si hay tarjeta y setea uidDecimal
String uidToDecimalString(const MFRC522::Uid &uid); // helper (opcional)

#endif
