#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include "imu_sensor.h"

// Pines del GY-61/ADXL335
// Se asume que estás usando pines ADC en tu ESP32/microcontrolador
const int xPin = A0; 
const int yPin = A1; 
const int zPin = A2;

// Referencias del ADC
const float VREF = 3.3;
const int ADC_RES = 4095; // 12 bits para ESP32
const float MID_POINT_V = VREF / 2.0; // Punto medio de 0g, generalmente 1.65V (3.3V/2)

// Sensibilidad del ADXL335: Típicamente 300 mV/g
// Rango +/- 3g. Esto es lo que permite convertir Voltaje -> Aceleración (g).
// 300 mV/g = 0.300 V/g.
const float SENSITIVITY_VG = 0.300; 

// Calibración: Valor de lectura analógica a 0g
// Esto debe ser determinado experimentalmente para mayor precisión, 
// pero usamos el punto medio como estimación inicial.
// (ADC_RES * MID_POINT_V) / VREF
const int OFFSET_0G_RAW = (int)((ADC_RES * MID_POINT_V) / VREF); 

void initVibrationSensor() {
  WiFi.mode(WIFI_STA);
  if(esp_now_init() != ESP_OK){
    Serial.println("Error inicializando ESP-NOW");
    return;
  }

  esp_now_peer_info_t peer = {};
  memset(&peer, 0, sizeof(peer));
  memcpy(peer.peer_addr, "\xFF\xFF\xFF\xFF\xFF\xFF", 6); // Broadcast
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  Serial.println("Sensor de vibración GY-61 y ESP-NOW inicializados");
    // Puedes agregar una pequeña rutina de calibración aquí 
    // para obtener un mejor valor de OFFSET_0G_RAW.
}

void sendVibrationData() {
  // Leer ADC (Mediciones de ACELERACIÓN)
  int rawX = analogRead(xPin);
  int rawY = analogRead(yPin);
  int rawZ = analogRead(zPin);

  // 1. Convertir a Voltaje (como lo tenías, pero no es estrictamente necesario 
    // si usamos las raw readings para restar el offset)
  float voltX = (rawX * VREF) / ADC_RES;
  float voltY = (rawY * VREF) / ADC_RES;
  float voltZ = (rawZ * VREF) / ADC_RES;
    
    // 2. Restar el OFFSET de 0g (El punto de equilibrio estático: 1.65V)
    // Esto AÍSLA la aceleración DINÁMICA (vibración).
    // Si la lectura es 1.65V, la resta da 0V, es decir, 0g de vibración.
    float dynamicVoltX = voltX - MID_POINT_V;
    float dynamicVoltY = voltY - MID_POINT_V;
    float dynamicVoltZ = voltZ - MID_POINT_V;

    // 3. Convertir el Voltaje Dinámico a Aceleración en 'g's
    // Aceleración (g) = Voltaje_Dinámico / Sensibilidad(V/g)
    float ax = dynamicVoltX / SENSITIVITY_VG;
    float ay = dynamicVoltY / SENSITIVITY_VG;
    float az = dynamicVoltZ / SENSITIVITY_VG;

  // **NOTA IMPORTANTE:**
    // Para medir la intensidad de la vibración, a menudo se usa la MAGNITUD (o RMS)
    // de estas aceleraciones dinámicas (aX, aY, aZ) o un alto 
    // *sampling rate* (frecuencia de muestreo) para hacer un análisis FFT.
    // Con este método estás enviando la aceleración instantánea, que es lo más 
    // directo. Si el dispositivo está en reposo, los valores deberían ser cercanos a cero.
    // Al vibrar, variarán rápidamente alrededor de cero.

  // Construir payload
  char payload[80];
  snprintf(payload, sizeof(payload),
      "ID:VIBRATION;X:%.2f,Y:%.2f,Z:%.2f", ax, ay, az); // Ahora envías aceleración en 'g's

  // Enviar por ESP-NOW
  esp_err_t result = esp_now_send((uint8_t*)"\xFF\xFF\xFF\xFF\xFF\xFF",
                  (uint8_t*)payload, strlen(payload)+1);
  if(result == ESP_OK) {
    Serial.println("Mensaje de vibración enviado");
    //Serial.println("X: " +  String(ax));
    //Serial.println("Y: " +  String(ay));
    //Serial.println("Z: " +  String(az));
  } else {
    Serial.println("Error enviando mensaje ESP-NOW");
  }
}