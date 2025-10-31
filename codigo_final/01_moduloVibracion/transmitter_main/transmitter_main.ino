#include "imu_sensor.h"

// --- Definiciones de Pines ---
// El usuario especificó D6 para LED y D7 para Botón
const int LED_PIN = D6;
const int BUTTON_PIN = D7;

// --- Parámetros de Control ---
const long BLINK_INTERVAL = 500; // 500 ms para el parpadeo (0.5 segundos)
const long TRANSMISSION_INTERVAL = 500; // 500 ms para la transmisión ESP-NOW
const long REQUIRED_PRESS_DURATION = 2000; // 2 segundos

// --- Variables de Estado del Sistema ---
// Define los dos modos de operación
enum SystemState {
    CALIBRATION_MODE, // LED Parpadeando, NO Transmite
    TRANSMIT_MODE     // LED Encendido, SÍ Transmite
};

SystemState currentState = CALIBRATION_MODE;
unsigned long last_blink_time = 0;
unsigned long last_transmission_time = 0;
unsigned long button_press_start_time = 0;
bool button_was_pressed = false;


// Función para manejar el parpadeo no bloqueante
void handleBlinking() {
    unsigned long current_time = millis();
    if (current_time - last_blink_time >= BLINK_INTERVAL) {
        // Invertir el estado del LED (HIGH/LOW)
        int led_state = digitalRead(LED_PIN);
        digitalWrite(LED_PIN, !led_state);
        last_blink_time = current_time;
    }
}

// Función para manejar el botón y la transición de estado
void handleButtonAndState() {
    // Lee el estado del botón. Usamos INPUT_PULLUP, por lo que LOW = presionado.
    int button_state = digitalRead(BUTTON_PIN);

    if (button_state == LOW) {
        // El botón está presionado
        if (!button_was_pressed) {
            // Registra el inicio de la pulsación
            button_press_start_time = millis();
            button_was_pressed = true;
        }
    } else { 
        // Botón liberado
        if (button_was_pressed) {
            unsigned long press_duration = millis() - button_press_start_time;

            if (press_duration >= REQUIRED_PRESS_DURATION) {
                // Se mantuvo presionado 2 segundos o más: ¡Cambiar de estado!
                currentState = TRANSMIT_MODE;
                digitalWrite(LED_PIN, HIGH); // Encender LED de forma sólida
                Serial.println("--- Transición a MODO TRANSMISIÓN (Led ON) ---");
            }
            button_was_pressed = false;
        }
    }
}

void setup() {
    Serial.begin(115200);
    // Inicializar pines: LED como salida, Botón como entrada con pull-up (asumiendo 
    // que el botón está cableado entre D7 y GND)
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP); 

    // Inicializar el sensor y ESP-NOW
    initVibrationSensor();

    // Estado inicial: Modo Calibración/Espera
    Serial.println("--- MODO CALIBRACIÓN (Led Parpadeando) ---");
    // Inicializa el estado del LED para que comience a parpadear inmediatamente
    digitalWrite(LED_PIN, LOW); 
    last_blink_time = millis();
}

void loop() {
    // 1. Siempre revisa el botón para permitir la transición de estado
    handleButtonAndState();

    if (currentState == CALIBRATION_MODE) {
        // 2. Si está en modo Calibración, solo parpadea y no transmite
        handleBlinking();
    } else { // currentState == TRANSMIT_MODE
        // 3. Si está en modo Transmisión, mantén el LED encendido y transmite datos
        unsigned long current_time = millis();
        
        // Transmitir cada 500 ms (no bloqueante)
        if (current_time - last_transmission_time >= TRANSMISSION_INTERVAL) {
            sendVibrationData();
            last_transmission_time = current_time;
        }
    }
}