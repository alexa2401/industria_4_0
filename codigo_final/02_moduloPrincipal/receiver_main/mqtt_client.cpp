#include "mqtt_client.h"
#include <WiFi.h>
#include <PubSubClient.h>

// ----- Configuración WiFi -----
const char* ssid = "Tec-IoT";
const char* password = "spotless.magnetic.bridge";

// ----- Configuración MQTT -----
const char* mqtt_server = "10.25.88.26";  // Dirección del broker MQTT
const int mqtt_port = 1883;
const char* mqtt_client_id = "ESP32_Receiver";
const char* topic = "datos/vibracion";

WiFiClient espClient;
PubSubClient client(espClient);

void reconnectMQTT();

void initMQTT() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConectado a WiFi correctamente.");
  Serial.print("Dirección IP asignada: ");
  Serial.println(WiFi.localIP());


  client.setServer(mqtt_server, mqtt_port);
  reconnectMQTT();
}

void loopMQTT() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Conectando al broker MQTT...");
    if (client.connect(mqtt_client_id)) {
      Serial.println(" Conectado!");
    } else {
      Serial.print(" Error (rc=");
      Serial.print(client.state());
      Serial.println("), reintentando en 5s...");
      delay(5000);
    }
  }
}

void publishMQTT(const char* topic, const char* payload) {
  if (client.connected()) {
    client.publish(topic, payload);
    Serial.print("Publicado en ");
    Serial.print(topic);
    Serial.print(": ");
    Serial.println(payload);
  } else {
    Serial.println("MQTT no conectado, no se pudo publicar");
  }
}
