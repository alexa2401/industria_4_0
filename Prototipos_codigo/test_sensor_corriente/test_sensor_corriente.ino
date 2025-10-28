// Lectura de sensor de corriente no invasivo SEN-11005 (SCT-013-030)
// Corriente máxima: 30A RMS -> 1V RMS
// Alejandro Araiza Escamilla - Versión Arduino IDE

const int analogPin = A0;       // Pin analógico (D0 en la XIAO ESP32C3)
const float VREF = 3.3;         // Voltaje de referencia del ADC
const int ADC_RES = 4095;       // Resolución de 12 bits (0-4095)
const float OFFSET = VREF / 2;  // 1.65 V - centro de la señal
const float CURRENT_FACTOR = 300.0; // 1V RMS = 30A RMS
const float CLIP_MIN = 6.0;     // Dead-zone: corrientes < 6A se van a 0

float getCurrentRMS(int samples) {
  double sumSq = 0;
  for (int i = 0; i < samples; i++) {
    int adcValue = analogRead(analogPin);
    float voltage = (adcValue * VREF) / ADC_RES;
    float centered = voltage - OFFSET;
    sumSq += centered * centered;
    delayMicroseconds(200); // ~5 kHz de muestreo
  }
  float meanSq = sumSq / samples;
  float vRMS = sqrt(meanSq);
  float currentRMS = vRMS * CURRENT_FACTOR;

  // --- Aplicar dead-zone: valores < 6A → 0, valores > 6A → proporcionales ---
  if (currentRMS < CLIP_MIN) {
    currentRMS = 0;
  } else {
    currentRMS = currentRMS - CLIP_MIN;
  }

  return currentRMS;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Lectura de corriente RMS iniciada...");
}

void loop() {
  float current = getCurrentRMS(1000);
  Serial.print(current, 2);
  Serial.println(" A");
  delay(1000);
}

