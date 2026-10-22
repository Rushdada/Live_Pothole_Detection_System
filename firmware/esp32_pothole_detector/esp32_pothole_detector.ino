/*
 * =====================================================================================
 * Project: IoT Model for Pothole Detection, Geolocation, and Alert Using Email
 * Hardware: ESP32 Development Board, NEO-6M GPS, HC-SR04 Ultrasonic, MPU-6050 IMU
 * =====================================================================================
 * Description:
 *   Continuously monitors vehicle undercarriage distance using HC-SR04 and vertical
 *   acceleration spikes using MPU-6050 accelerometer. Reads real-time latitude,
 *   longitude, and speed from the NEO-6M GPS module via HardwareSerial2.
 *   
 *   When a pothole is detected:
 *   1. Evaluates severity based on depth drop (cm) and impact shock (g).
 *   2. Outputs structured JSON telemetry over Serial (115200 baud) to Edge computer.
 *   3. Optional: Connects to WiFi and dispatches alert directly.
 * =====================================================================================
 */

#include <Wire.h>
#include <TinyGPS++.h>
#include <WiFi.h>

// ----------------- PIN DEFINITIONS -----------------
// HC-SR04 Ultrasonic Sensor
#define TRIG_PIN 5
#define ECHO_PIN 18

// NEO-6M GPS Module (Serial2 on ESP32: RX=16, TX=17)
#define GPS_RX_PIN 16
#define GPS_TX_PIN 17
#define GPS_BAUD 9600

// Status & Alert LEDs / Buzzer
#define LED_STATUS_PIN 2     // Onboard LED
#define BUZZER_PIN 4         // Optional buzzer for audio alert

// ----------------- MPU-6050 REGISTERS -----------------
const int MPU_ADDR = 0x68;   // I2C address of MPU-6050

// ----------------- DETECTION THRESHOLDS -----------------
float baselineClearanceCm = 20.0;    // Calibrated on flat road
const float MINOR_DEPTH_DROP = 4.0;  // 4cm drop
const float SEVERE_DEPTH_DROP = 9.0; // 9cm drop
const float VIBRATION_SPIKE_G = 1.6; // Vertical acceleration threshold (1.0g is normal gravity)
const unsigned long COOLDOWN_MS = 3000; // 3-second cooldown between detections

// ----------------- OBJECTS & STATE -----------------
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

unsigned long lastDetectionTime = 0;
float currentLat = 0.0;
float currentLng = 0.0;
float currentSpeedKmh = 0.0;

// Function Prototypes
void initMPU6050();
void readAccelerometer(float &ax, float &ay, float &az);
float readUltrasonicDistanceCm();
void calibrateGroundClearance();

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[SYSTEM] Booting Pothole Detection & Geolocation Unit...");

  // Pin modes
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_STATUS_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  // Initialize I2C for MPU-6050
  Wire.begin(21, 22); // SDA=21, SCL=22
  initMPU6050();

  // Initialize GPS UART
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("[GPS] Listening for NMEA sentences on Serial2...");

  // Calibrate nominal clearance on flat surface
  calibrateGroundClearance();

  Serial.println("[SYSTEM] Ready! Scanning road conditions...");
  digitalWrite(LED_STATUS_PIN, HIGH);
}

void loop() {
  // 1. Process incoming GPS bytes
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  if (gps.location.isValid()) {
    currentLat = gps.location.lat();
    currentLng = gps.location.lng();
    currentSpeedKmh = gps.speed.kmph();
  }

  // 2. Measure Ultrasonic Distance
  float measuredDistance = readUltrasonicDistanceCm();

  // 3. Measure Accelerometer Vertical Force
  float ax = 0, ay = 0, az = 0;
  readAccelerometer(ax, ay, az);
  float vibrationG = abs(az); // Normal is ~1.0g

  // 4. Evaluate Pothole Conditions
  float depthDrop = measuredDistance - baselineClearanceCm;
  unsigned long now = millis();

  bool isPothole = false;
  String severity = "LOW";

  if (now - lastDetectionTime > COOLDOWN_MS) {
    if (depthDrop >= SEVERE_DEPTH_DROP || vibrationG >= 2.6) {
      isPothole = true;
      severity = "HIGH";
    } else if (depthDrop >= MINOR_DEPTH_DROP || vibrationG >= VIBRATION_SPIKE_G) {
      isPothole = true;
      severity = (depthDrop >= 7.0 || vibrationG >= 2.0) ? "MEDIUM" : "LOW";
    }
  }

  // 5. Handle Detection Event
  if (isPothole) {
    lastDetectionTime = now;

    // Audible / visual alert
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);

    // Emit structured JSON over USB Serial for Edge Companion / Python Server
    Serial.print("{\"type\":\"POTHOLE\",\"lat\":");
    Serial.print(currentLat, 6);
    Serial.print(",\"lng\":");
    Serial.print(currentLng, 6);
    Serial.print(",\"dist\":");
    Serial.print(measuredDistance, 1);
    Serial.print(",\"depth\":");
    Serial.print(depthDrop, 1);
    Serial.print(",\"vib\":");
    Serial.print(vibrationG, 2);
    Serial.print(",\"spd\":");
    Serial.print(currentSpeedKmh, 1);
    Serial.print(",\"severity\":\"");
    Serial.print(severity);
    Serial.println("\"}");
  } else {
    // Normal periodic telemetry output (every 500ms)
    static unsigned long lastTelemetry = 0;
    if (now - lastTelemetry > 500) {
      lastTelemetry = now;
      Serial.print("{\"lat\":");
      Serial.print(currentLat, 6);
      Serial.print(",\"lng\":");
      Serial.print(currentLng, 6);
      Serial.print(",\"dist\":");
      Serial.print(measuredDistance, 1);
      Serial.print(",\"vib\":");
      Serial.print(vibrationG, 2);
      Serial.print(",\"spd\":");
      Serial.print(currentSpeedKmh, 1);
      Serial.println("}");
    }
  }

  delay(50);
}

// ----------------- SENSOR HELPER FUNCTIONS -----------------

void initMPU6050() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // Wake up MPU-6050
  Wire.endTransmission(true);
  Serial.println("[IMU] MPU-6050 initialized.");
}

void readAccelerometer(float &ax, float &ay, float &az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  if (Wire.available() >= 6) {
    int16_t rawX = Wire.read() << 8 | Wire.read();
    int16_t rawY = Wire.read() << 8 | Wire.read();
    int16_t rawZ = Wire.read() << 8 | Wire.read();

    // Default sensitivity scale factor is 16384 LSB/g for +/- 2g range
    ax = rawX / 16384.0;
    ay = rawY / 16384.0;
    az = rawZ / 16384.0;
  }
}

float readUltrasonicDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  if (duration == 0) return baselineClearanceCm; // Return baseline if out of range

  // Speed of sound: 343 m/s = 0.0343 cm/microsecond. Divide by 2 for round-trip.
  float distance = (duration * 0.0343) / 2.0;
  return distance;
}

void calibrateGroundClearance() {
  Serial.println("[CALIB] Measuring baseline road clearance...");
  float sum = 0;
  int validSamples = 0;

  for (int i = 0; i < 20; i++) {
    float d = readUltrasonicDistanceCm();
    if (d > 10.0 && d < 60.0) {
      sum += d;
      validSamples++;
    }
    delay(50);
  }

  if (validSamples > 0) {
    baselineClearanceCm = sum / validSamples;
    Serial.print("[CALIB] Baseline Clearance established: ");
    Serial.print(baselineClearanceCm);
    Serial.println(" cm");
  } else {
    Serial.println("[CALIB] Warning: Defaulting to 20.0 cm clearance.");
  }
}

