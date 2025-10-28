#include "rfid_reader.h"
#include <SPI.h>
#include <MFRC522.h>

// Pines según tu conexión
static const uint8_t RST_PIN  = 2;  // RST -> D2 (GPIO2)
static const uint8_t SS_PIN   = 5;  // SS/SDA -> GPIO5
static const uint8_t SCK_PIN  = 18; // SCK -> GPIO18
static const uint8_t MISO_PIN = 19; // MISO -> GPIO19
static const uint8_t MOSI_PIN = 23; // MOSI -> GPIO23

// Crear instancia MFRC522 usando SPI con pines personalizados
MFRC522 mfrc522(SS_PIN, RST_PIN);

void initRFID() {
    // Iniciar SPI con pines personalizados
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
    mfrc522.PCD_Init();
    Serial.println("RFID listo con SPI personalizado.");
}

bool checkForCard(uint64_t &uidDecimal) {
    if (!mfrc522.PICC_IsNewCardPresent()) return false;
    if (!mfrc522.PICC_ReadCardSerial()) return false;

    uidDecimal = 0;
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        uidDecimal <<= 8;
        uidDecimal |= mfrc522.uid.uidByte[i];
    }

    mfrc522.PICC_HaltA(); // Para detener la tarjeta hasta próxima lectura
    return true;
}

