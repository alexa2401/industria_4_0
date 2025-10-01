#include <Wire.h>
#include <math.h>

#define MPU_ADDR 0x68
#define PWR_MGMT_1 0x6B
#define ACCEL_CONFIG 0x1C
#define ACCEL_XOUT_H 0x3B

const int16_t SENSITIVITY[] = {16384, 8192, 4096, 2048};
int accel_fs_index = 0; // ±2g
float accel_scale = 1.0 / 16384.0;

float alpha = 0.24; // filtro EWMA
float filt_ax = 0, filt_ay = 0, filt_az = 0;

float FS_g = 2.0; // rango en g (2,4,8,16)
const float SQRT3 = 1.7320508075688772;

void writeRegister(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

void setAccelRange(int fs_index) {
  accel_fs_index = constrain(fs_index, 0, 3);
  uint8_t val = (accel_fs_index << 3);
  writeRegister(ACCEL_CONFIG, val);
  accel_scale = 1.0f / (float)SENSITIVITY[accel_fs_index];
  // Actualiza FS_g
  if (accel_fs_index == 0) FS_g = 2.0;
  else if (accel_fs_index == 1) FS_g = 4.0;
  else if (accel_fs_index == 2) FS_g = 8.0;
  else FS_g = 16.0;
}

int16_t read16(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2);
  while (Wire.available() < 2);
  uint8_t hi = Wire.read();
  uint8_t lo = Wire.read();
  return (int16_t)((hi << 8) | lo);
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  delay(100);
  writeRegister(PWR_MGMT_1, 0x00);
  delay(50);
  setAccelRange(0); // ±2g (cambia si quieres)
}

void loop() {
  int16_t raw_ax = read16(ACCEL_XOUT_H + 0);
  int16_t raw_ay = read16(ACCEL_XOUT_H + 2);
  int16_t raw_az = read16(ACCEL_XOUT_H + 4);

  float ax = raw_ax * accel_scale; // en g
  float ay = raw_ay * accel_scale;
  float az = raw_az * accel_scale;

  // Filtrar
  filt_ax = alpha * ax + (1.0 - alpha) * filt_ax;
  filt_ay = alpha * ay + (1.0 - alpha) * filt_ay;
  filt_az = alpha * az + (1.0 - alpha) * filt_az;

  // Magnitud total (incluye gravedad)
  float mag = sqrtf(filt_ax * filt_ax + filt_ay * filt_ay + filt_az * filt_az);

  // Opción A: normalizar a 0..1 usando FS * sqrt(3)
  float denomA = FS_g * SQRT3;
  float normA = mag / denomA;
  if (normA < 0) normA = 0;
  if (normA > 1) normA = 1;

  // Opción B: normalizar dinámicamente restando 1g (gravedad aproximada)
  float denomB = FS_g * SQRT3 - 1.0; // evita dividir por cero (para FS>0)
  float normB = 0.0;
  if (denomB > 0.0) {
    normB = (mag - 1.0) / denomB;
    if (normB < 0) normB = 0;
    if (normB > 1) normB = 1;
  }

  // Salidas por serial
  //Serial.print("g filt: ");
  //Serial.print(filt_ax, 3); Serial.print(", ");
  //Serial.print(filt_ay, 3); Serial.print(", ");
  //Serial.print(filt_az, 3);

 // Serial.print("  | mag: "); Serial.print(mag, 4);
  //Serial.print("  | normA: "); Serial.print(normA, 4); // total
  //Serial.print("  | normB: "); Serial.println(normB, 4); // dinámica

  if(normA > 0.4)
  {
    Serial.println("Peligro");
  }else if (normA >= 0.3)
  {
    Serial.println("Vibrando");
  }else if (normA >= 0.0)
  {
    Serial.println("Reposo");
  }

  Serial.print("NormA: "); Serial.println(normA, 4);

  delay(100); // ~100 Hz
}

