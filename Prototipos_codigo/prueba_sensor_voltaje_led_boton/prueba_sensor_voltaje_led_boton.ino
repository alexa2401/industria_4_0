const int LED_PIN = D5;
const int BUTTON_PIN = D4;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    digitalWrite(LED_PIN, HIGH);  // LED encendido cuando se presiona
  } else {
    digitalWrite(LED_PIN, LOW);   // LED apagado cuando se suelta
  }
}
