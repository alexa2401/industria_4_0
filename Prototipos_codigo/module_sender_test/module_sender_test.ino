#include <WiFi.h>
#include <esp_now.h>

// Pines del GY-61
#define xPin D0
#define yPin D1
#define zPin D2

// Estructura del mensaje
typedef struct struct_message {
  float ax;
  float ay;
  float az;
} struct_message;

struct_message myData;

// Dirección broadcast (para enviar a todos los receptores)
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// Callback de envío actualizado para ESP-IDF v5
#if ESP_IDF_VERSION_MAJOR >= 5
void onSend(const wifi_tx_info_t *mac_addr, esp_now_send_status_t status) {
#else
void onSend(const uint8_t *mac_addr, esp_now_send_status_t status) {
#endif
  Serial.print("Estado del envío: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Éxito" : "Fallo");
}

// Leer GY-61 y convertir a g
void readIMU() {
  int rawX = analogRead(xPin);
  int rawY = analogRead(yPin);
  int rawZ = analogRead(zPin);

  // Conversión básica (asumiendo 0g ≈ 1.65 V y sensibilidad ~330 mV/g)
  // ADC del XIAO-ESP32-C3 = 12 bits (0–4095) con 3.3 V referencia
  float voltageX = (rawX / 4095.0) * 3.3;
  float voltageY = (rawY / 4095.0) * 3.3;
  float voltageZ = (rawZ / 4095.0) * 3.3;

  float zeroG = 1.65;       // Voltaje en reposo (ajusta si tu sensor tiene offset)
  float sensitivity = 0.33; // 330 mV/g (para ADXL335)
  
  myData.ax = (voltageX - zeroG) / sensitivity;
  myData.ay = (voltageY - zeroG) / sensitivity;
  myData.az = (voltageZ - zeroG) / sensitivity;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(xPin, INPUT);
  pinMode(yPin, INPUT);
  pinMode(zPin, INPUT);

  WiFi.mode(WIFI_STA);
  Serial.println("XIAO ESP32-C3 Sender iniciado");
  Serial.print("MAC local: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al inicializar ESP-NOW");
    return;
  }

  esp_now_register_send_cb(onSend);

  // Añadir el peer broadcast
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Error al añadir peer");
    return;
  }

  Serial.println("ESP-NOW inicializado correctamente");
}

void loop() {
  readIMU();  // Leer sensor

  Serial.print("ax: "); Serial.print(myData.ax);
  Serial.print("\tay: "); Serial.print(myData.ay);
  Serial.print("\taz: "); Serial.println(myData.az);

  // Enviar por ESP-NOW
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&myData, sizeof(myData));

  if (result == ESP_OK) {
    Serial.println("Datos enviados correctamente\n");
  } else {
    Serial.print("Error al enviar datos: ");
    Serial.println(result);
  }

  delay(1000); // Enviar cada 1 segundo
}
