// Lectura simple de UID con RC522 y ESP32
// Wiring (según tu mensaje):
// VCC -> 3V3 (o VIN si tu módulo requiere 5V)
// GND -> GND
// RST -> GPIO2
// SDA/SS -> GPIO5
// SCK -> GPIO18
// MISO -> GPIO19
// MOSI -> GPIO23

#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 5     // SDA / SS
#define RST_PIN 2    // RST

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; } // espera Serial en algunos entornos
  // Inicializa SPI con pines del ESP32 (SCK, MISO, MOSI)
  SPI.begin(18, 19, 23);
  mfrc522.PCD_Init();
  Serial.println();
  Serial.println("RC522 inicializado. Acerca la tarjeta...");
}

void loop() {
  // ¿Hay una nueva tarjeta presente?
  if (!mfrc522.PICC_IsNewCardPresent()) {
    delay(50);
    return;
  }

  // ¿Se pudo leer la tarjeta?
  if (!mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // Mostrar UID en HEX y calcular decimal
  Serial.print("UID (hex): ");
  String uidHex = "";
  unsigned long long uidDec = 0ULL; // para UID hasta 8 bytes (seguro para la mayoría)
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) Serial.print("0");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial.print(" ");
    // Construimos un número decimal (big-endian concatenado)
    uidDec = (uidDec << 8) | mfrc522.uid.uidByte[i];
  }
  Serial.println();

  Serial.print("UID (dec): ");
  Serial.println(uidDec);

  // Tipo de tarjeta (PICC)
  MFRC522::PICC_Type piccType = mfrc522.PICC_GetType(mfrc522.uid.sak);
  Serial.print("Tipo de tarjeta: ");
  Serial.println(mfrc522.PICC_GetTypeName(piccType));

  // Opcional: puedes guardar el UID en una variable para comparar/identificar
  // Ejemplo rápido de formato legible (ej: "AA:BB:CC:DD")
  String uidStr = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) uidStr += "0";
    uidStr += String(mfrc522.uid.uidByte[i], HEX);
    if (i < mfrc522.uid.size - 1) uidStr += ":";
  }
  uidStr.toUpperCase();
  Serial.print("UID formatted: ");
  Serial.println(uidStr);

  // Finalizar lectura
  mfrc522.PICC_HaltA();           // detener la PICC
  mfrc522.PCD_StopCrypto1();      // detener cifrado si se abrió
  delay(500);                     // pequeño retraso para evitar lecturas rápidas repetidas
}
