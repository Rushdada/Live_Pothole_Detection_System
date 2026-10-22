/*
 * =====================================================================================
 * Project: IoT Pothole Detection & Geolocation Unit (Arduino Uno / Nano)
 * Hardware: Arduino Uno R3, NEO-6M GPS, HC-SR04 Ultrasonic, MPU-6050 Accelerometer
 * =====================================================================================
 * Pinout Connections:
 *   - NEO-6M GPS: VCC->5V, GND->GND, TX->Pin 4 (Arduino RX), RX->Pin 3 (Arduino TX)
 *   - HC-SR04: VCC->5V, GND->GND, TRIG->Pin 9, ECHO->Pin 10
 *   - MPU-6050: VCC->5V, GND->GND, SDA->A4, SCL->A5
 *   - LED Indicator: Pin 13
 * =====================================================================================
 */

#include <Wire.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>

// Pins
#define TRIG_PIN 9
#define ECHO_PIN 10
#define GPS_RX 4
#define GPS_TX 3
#define LED_PIN 13

// Thresholds
const float NOMINAL_CLEARANCE = 20.0; // cm
const float MIN_DROP_CM = 4.0;
const float VIB_SPIKE_G = 1.6;

TinyGPSPlus gps;
SoftwareSerial gpsSerial(GPS_RX, GPS_TX);

const int MPU_ADDR = 0x68;
unsigned long lastAlertTime = 0;

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  Wire.begin();
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);

  Serial.println(F("[SYSTEM] Arduino Pothole Detector Initialized."));
}

float getUltrasonicDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 25000);
  if (dur == 0) return NOMINAL_CLEARANCE;
  return (dur * 0.0343) / 2.0;
}

float getZAcceleration() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3F); // ACCEL_ZOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 2, true);
  if (Wire.available() >= 2) {
    int16_t rawZ = Wire.read() << 8 | Wire.read();
    return abs(rawZ / 16384.0);
  }
  return 1.0;
}

void loop() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  float dist = getUltrasonicDistance();
  float vib = getZAcceleration();
  float depthDrop = dist - NOMINAL_CLEARANCE;

  float lat = gps.location.isValid() ? gps.location.lat() : 0.0;
  float lng = gps.location.isValid() ? gps.location.lng() : 0.0;
  float spd = gps.speed.isValid() ? gps.speed.kmph() : 0.0;

  unsigned long now = millis();
  if (now - lastAlertTime > 3000) {
    if (depthDrop >= MIN_DROP_CM || vib >= VIB_SPIKE_G) {
      lastAlertTime = now;
      digitalWrite(LED_PIN, HIGH);

      // Output JSON frame to USB Serial
      Serial.print(F("{\"type\":\"POTHOLE\",\"lat\":"));
      Serial.print(lat, 6);
      Serial.print(F(",\"lng\":"));
      Serial.print(lng, 6);
      Serial.print(F(",\"dist\":"));
      Serial.print(dist, 1);
      Serial.print(F(",\"depth\":"));
      Serial.print(depthDrop, 1);
      Serial.print(F(",\"vib\":"));
      Serial.print(vib, 2);
      Serial.print(F(",\"spd\":"));
      Serial.print(spd, 1);
      Serial.println(F("}"));

      delay(100);
      digitalWrite(LED_PIN, LOW);
    }
  }

  delay(60);
}

