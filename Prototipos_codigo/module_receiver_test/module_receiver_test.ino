#include <WiFi.h>
#include <esp_now.h>

// Estructura idéntica al sender
typedef struct struct_message {
  float ax;
  float ay;
  float az;
} struct_message;

struct_message incomingData;

// Callback de recepción actualizado a ESP-IDF v5
#if ESP_IDF_VERSION_MAJOR >= 5
void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
#else
void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
#endif
  if (len != sizeof(struct_message)) {
    Serial.print("Paquete inesperado: len=");
    Serial.println(len);
    return;
  }

  // Copiar datos recibidos a la estructura
  memcpy(&incomingData, data, sizeof(incomingData));

#if ESP_IDF_VERSION_MAJOR >= 5
  // Imprimir MAC del remitente
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
           info->src_addr[0], info->src_addr[1], info->src_addr[2],
           info->src_addr[3], info->src_addr[4], info->src_addr[5]);
  Serial.print("Paquete recibido de: ");
  Serial.println(macStr);
#endif

  // Mostrar datos
  Serial.print("ax: "); Serial.print(incomingData.ax);
  Serial.print("\tay: "); Serial.print(incomingData.ay);
  Serial.print("\taz: "); Serial.println(incomingData.az);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Configurar Wi-Fi en modo estación
  WiFi.mode(WIFI_STA);
  Serial.println("📡 ESP32 Receiver iniciado");
  Serial.print("MAC local: ");
  Serial.println(WiFi.macAddress());

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error al inicializar ESP-NOW");
    return;
  }

  // Registrar callback de recepción
  esp_now_register_recv_cb(onRecv);

  Serial.println("Listo para recibir datos...");
}

void loop() {
  // Nada aquí, todo se maneja en el callback
}
