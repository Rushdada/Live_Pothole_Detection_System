# IoT Pothole Detection & Geolocation System - Wiring & Circuit Guide

This guide details the complete hardware connections, pinout tables, component specifications, and physical vehicle installation instructions for the **IoT Pothole Detection, Geolocation & Email Alert Unit**.

---

## 1. Hardware Bill of Materials (BOM)

| Component | Quantity | Purpose | Operating Voltage |
| :--- | :---: | :--- | :---: |
| **ESP32 DevKit V1** (or Arduino Uno) | 1 | Master Edge Controller & Processing | 3.3V / 5V (USB) |
| **NEO-6M GPS Module with Antenna** | 1 | Latitude, Longitude, & Vehicle Speed tracking | 3.3V - 5.0V |
| **HC-SR04 Ultrasonic Distance Sensor** | 1 | Measures road clearance drop / pothole depth | 5.0V |
| **MPU-6050 6-Axis IMU (Accel + Gyro)** | 1 | Measures vertical Z-axis jerk / vibration impact | 3.3V - 5.0V |
| **Active 5V Buzzer & Red LED** | 1 each | In-cabin real-time driver alert | 3.3V - 5.0V |
| **Breadboard / Perfboard & Jumper Wires** | 1 set | Circuit prototyping & harness wiring | - |
| **12V to 5V Step-Down (LM2596 / USB Car Charger)** | 1 | Vehicle accessory socket power regulator | 12V in / 5V out |

---

## 2. Wiring Connections

### A. ESP32 Pinout Configuration

```
+-------------------------------------------------------------------------+
|                              ESP32 DEVKIT                               |
|                                                                         |
|      [3V3 / VIN] --------+--------------+--------------+                |
|      [GND] --------------+--------------+--------------+                |
|                                                                         |
|      [GPIO 21] (I2C SDA) <============> MPU-6050 SDA                    |
|      [GPIO 22] (I2C SCL) <============> MPU-6050 SCL                    |
|                                                                         |
|      [GPIO 16] (RX2)     <============> NEO-6M GPS TX                   |
|      [GPIO 17] (TX2)     <============> NEO-6M GPS RX (Optional)        |
|                                                                         |
|      [GPIO 5]  (Output)  -------------> HC-SR04 TRIG                    |
|      [GPIO 18] (Input)   <------------- HC-SR04 ECHO (via Voltage Div)  |
|                                                                         |
|      [GPIO 2]  (Output)  -------------> Status LED                      |
|      [GPIO 4]  (Output)  -------------> Active Buzzer                   |
+-------------------------------------------------------------------------+
```

#### Detailed Pin Mapping Table:

| Sensor Module | Sensor Pin | ESP32 Pin | Logic Level / Note |
| :--- | :--- | :--- | :--- |
| **NEO-6M GPS** | VCC | `VIN` or `5V` | Ensure patch antenna faces upward to sky |
| | GND | `GND` | Common ground |
| | TX | `GPIO 16` (RX2) | Transmits NMEA sentences to ESP32 |
| | RX | `GPIO 17` (TX2) | Configuration commands (optional) |
| **MPU-6050 IMU** | VCC | `3V3` | Powered by 3.3V rail |
| | GND | `GND` | Common ground |
| | SDA | `GPIO 21` | I2C Data line |
| | SCL | `GPIO 22` | I2C Clock line |
| **HC-SR04 Ultrasonic** | VCC | `VIN` (5V) | Requires 5V supply |
| | GND | `GND` | Common ground |
| | TRIG | `GPIO 5` | Ultrasonic trigger pulse (10 µs) |
| | ECHO | `GPIO 18` | Use 1kΩ / 2kΩ voltage divider to step 5V to 3.3V |
| **Active Buzzer** | Positive (+) | `GPIO 4` | Audio beep on detection |
| | Negative (-) | `GND` | Common ground |

> [!NOTE]
> **Voltage Divider for HC-SR04 ECHO Pin on ESP32:**
> The ESP32 GPIOs operate at 3.3V logic. Because HC-SR04 outputs a 5V echo pulse, connect a simple voltage divider between the Echo pin and ESP32 GPIO 18 (e.g. 1kΩ series resistor and 2kΩ pull-down resistor to GND) to protect the pin.

---

### B. Arduino Uno Pinout Configuration (Alternative Low-Cost Setup)

| Sensor Module | Sensor Pin | Arduino Uno Pin |
| :--- | :--- | :--- |
| **NEO-6M GPS** | TX | `Pin 4` (SoftwareSerial RX) |
| | RX | `Pin 3` (SoftwareSerial TX) |
| | VCC | `5V` |
| | GND | `GND` |
| **HC-SR04 Ultrasonic** | TRIG | `Pin 9` |
| | ECHO | `Pin 10` |
| | VCC | `5V` |
| | GND | `GND` |
| **MPU-6050 IMU** | SDA | `A4` (I2C SDA) |
| | SCL | `A5` (I2C SCL) |
| | VCC | `5V` / `3.3V` |
| | GND | `GND` |
| **Status LED** | Anode (+) | `Pin 13` (Built-in LED) |

---

## 3. Vehicle Installation & Mounting Recommendations

1. **Ultrasonic Sensor Placement:**
   - Mount securely beneath the vehicle's front bumper or undercarriage, pointed straight down perpendicular to the road.
   - Recommended nominal ground clearance height: **18 cm to 28 cm**.
   - Ensure the sensor cone of vision is clear of front spoilers, tires, and exhaust pipes.
   - Waterproof / rubberized ultrasonic transducers (such as JSN-SR04T) are recommended for harsh weather or rain conditions.

2. **MPU-6050 Accelerometer Placement:**
   - Mount firmly to the vehicle chassis or lower suspension arm.
   - Ensure the Z-axis is aligned vertically (pointing straight up) so nominal road driving registers 1.0g (standard Earth gravity).

3. **NEO-6M GPS Antenna Placement:**
   - Mount the ceramic patch antenna on top of the dashboard or exterior roof.
   - The metallic side must face skyward with an unobstructed view of the horizon for fast satellite lock (PPS LED will begin blinking once fixed).

4. **Power Supply:**
   - Power the microcontroller using a standard 5V/2A USB car charger plugged into the vehicle's 12V cigarette lighter accessory port.

