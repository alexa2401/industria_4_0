#include "current_sensor.h"

const int LED_PIN = D3;
const int BUTTON_PIN = D4;

const long BLINK_INTERVAL = 500;
const long TRANSMISSION_INTERVAL = 500;
const long REQUIRED_PRESS_DURATION = 2000;

enum SystemState {
    CALIBRATION_MODE,
    TRANSMIT_MODE
};

SystemState currentState = CALIBRATION_MODE;
unsigned long last_blink_time = 0;
unsigned long last_transmission_time = 0;
unsigned long button_press_start_time = 0;
bool button_was_pressed = false;

void handleBlinking() {
    unsigned long t = millis();
    if (t - last_blink_time >= BLINK_INTERVAL) {
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        last_blink_time = t;
    }
}

void handleButtonAndState() {
    int button_state = digitalRead(BUTTON_PIN);

    if (button_state == LOW) {
        if (!button_was_pressed) {
            button_press_start_time = millis();
            button_was_pressed = true;
        }
    } else {
        if (button_was_pressed) {
            unsigned long duration = millis() - button_press_start_time;

            if (duration >= REQUIRED_PRESS_DURATION) {
                currentState = TRANSMIT_MODE;
                digitalWrite(LED_PIN, HIGH);
                Serial.println("--- MODO TRANSMISIÓN ---");
            }
            button_was_pressed = false;
        }
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);

    initCurrentSensor();

    Serial.println("--- MODO CALIBRACIÓN (LED Parpadeando) ---");
    digitalWrite(LED_PIN, LOW);
    last_blink_time = millis();
}

void loop() {
    handleButtonAndState();

    if (1 == 0) {
        handleBlinking();
    } 
    else {
        unsigned long t = millis();
        if (t - last_transmission_time >= TRANSMISSION_INTERVAL) {
            sendCurrentData();
            last_transmission_time = t;
        }
    }
}
