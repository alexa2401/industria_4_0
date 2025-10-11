// Pines
const int xPin = D0;
const int yPin = D1;
const int zPin = D2;

const int ledPin = D6;
const int buttonPin = D7;

bool ledState = false;  // Estado actual del LED
bool lastButtonState = HIGH;  // Estado previo (para detección de cambio)

void setup() {
  Serial.begin(115200);

  pinMode(ledPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);  // Botón con pull-up interno

  digitalWrite(ledPin, LOW);  // LED apagado al inicio

  Serial.println("Lectura GY-61 iniciada...");
}

void loop() {
  // === LECTURA DEL BOTÓN ===
  bool buttonState = digitalRead(buttonPin);

  // Detectar flanco de bajada (cuando se presiona)
  if (buttonState == LOW && lastButtonState == HIGH) {
    ledState = !ledState;  // Cambia el estado del LED
    digitalWrite(ledPin, ledState);
    delay(200);  // Anti-rebote básico
  }
  lastButtonState = buttonState;

  // === LECTURA DEL GY-61 ===
  int xValue = analogRead(xPin);
  int yValue = analogRead(yPin);
  int zValue = analogRead(zPin);

  // Mostrar lecturas
  Serial.print("X: "); Serial.print(xValue);
  Serial.print("\tY: "); Serial.print(yValue);
  Serial.print("\tZ: "); Serial.print(zValue);
  Serial.print("\tLED: "); Serial.println(ledState ? "ON" : "OFF");

  delay(500);  // Medio segundo entre lecturas
}
