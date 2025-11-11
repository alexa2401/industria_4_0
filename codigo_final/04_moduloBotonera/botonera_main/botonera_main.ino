#include "botonera.h"

void setup() {
    Serial.begin(115200);
    initBotonera();
}

void loop() {
    updateBotonera();
}
