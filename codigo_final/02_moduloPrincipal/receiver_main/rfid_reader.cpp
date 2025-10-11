#include "rfid_reader.h"
#include <SPI.h>
#include <MFRC522.h>

// Pines (ajusta si tu placa mapea D2 distinto)
static const uint8_t RST_PIN = 2;  // RST -> D2 (GPIO2)
static const uint8_t SS_PIN  = 5;  // SS/SDA -> GPIO5

// SPI bus pins (ESP32)
static const uint8_t SCK_PIN  = 18; // SCK -> GPIO18
static const uint8_t MISO_PIN = 19; // MISO -> GPIO19
static const uint8_t MOSI_PIN = 23; // MOSI -> GPIO23

static MFRC522 mfrc(SS_PIN, RST_PIN);

void initRFID() {
  // Inicializar SPI con pines explícitos
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
  mfrc.PCD_Init();
  delay(50);
  Serial.println("RFID RC522 inicializado");
}

bool checkForCard(uint64_t &uidDecimal) {
  // Retorna true si encuentra y lee correctamente una tarjeta, y setea uidDecimal
  if (!mfrc.PICC_IsNewCardPresent()) return false;
  if (!mfrc.PICC_ReadCardSerial()) return false;

  // Convertir UID (array de bytes) a decimal acumulando como base 256
  uidDecimal = 0;
  for (byte i = 0; i < mfrc.uid.size; i++) {
    uidDecimal = (uidDecimal << 8) | mfrc.uid.uidByte[i];
  }

  // Finalizar lectura del PICC
  mfrc.PICC_HaltA();
  mfrc.PCD_StopCrypto1();

  return true;
}

// helper opcional: devuelve el decimal en formato String (para debug)
String uidToDecimalString(const MFRC522::Uid &uid) {
  uint64_t dec = 0;
  for (byte i = 0; i < uid.size; i++) {
    dec = (dec << 8) | uid.uidByte[i];
  }
  return String(dec);
}
