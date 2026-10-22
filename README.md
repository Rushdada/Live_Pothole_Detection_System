# IoT Pothole Detection, Geolocation & Email Alert System

An end-to-end IoT and software solution for automated road condition monitoring. The system detects potholes using ultrasonic and accelerometer sensors, pinpoints their exact GPS coordinates, and dispatches real-time email alerts containing severity metrics and direct Google Maps navigation links to road maintenance authorities.

---

## 🌟 Key Features

- **📱 Interactive Mobile Camera Scanner App (`/mobile`):** Beginner-friendly, responsive mobile app that accesses your smartphone's rear road camera, streams live video, and performs real-time AI pothole detection.
- **📷 Live Camera Bounding Boxes & Snapshots:** Detects potholes in the camera feed, marks red hazard bounding boxes on screen with audio/haptic feedback, and embeds the captured photo directly into the email alert!
- **📧 Real-time Email Alerts to rushipapu456@gmail.com:** Automatically dispatches alerts containing the live photo, exact GPS coordinates, depth estimation, and a 1-click Google Maps link.
- **📱 One-Scan Mobile Connect (QR Code):** Simply click "Phone QR" on the desktop dashboard to scan and instantly launch the mobile app on your Android or iPhone over Wi-Fi.
- **Automated Dual-Sensor Detection:** Fuses ultrasonic depth drop ($\Delta d$) with vertical accelerometer shock ($a_z$) to detect potholes and filter out speed bumps or rough surfaces.
- **Accurate GPS Geolocation:** Logs exact latitude, longitude, and vehicle speed via the NEO-6M GPS module or phone GPS.
- **Interactive Web GIS Dashboard:** Live OpenStreetMap / Leaflet interface with real-time vehicle tracking, sensor gauges, and incident management.
- **Turnkey Vehicle Simulation:** Test and demonstrate the full system immediately on your computer or mobile device.
- **Physical Hardware Firmware Included:** Complete C++ firmware for **ESP32** and **Arduino Uno**.

---

## 📁 Project Structure

```text
├── app.py                             # Flask Web Server & REST API
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment & SMTP configuration template
├── README.md                          # Quickstart & user guide
├── PROJECT_REPORT.md                  # Comprehensive academic / engineering project report
├── WIRING_AND_CIRCUIT_GUIDE.md        # Hardware wiring pinouts and sensor placement guide
│
├── src/
│   ├── config.py                      # System configuration & thresholds
│   ├── database.py                    # SQLite database management & queries
│   ├── detector.py                    # Sensor fusion & pothole classification engine
│   ├── email_service.py               # SMTP client & HTML alert template generator
│   ├── serial_reader.py               # Hardware USB COM port listener
│   └── simulator.py                   # Virtual vehicle drive & telemetry generator
│
├── templates/
│   └── index.html                     # Interactive Leaflet GIS Dashboard
│
├── static/
│   ├── css/style.css                  # Modern dashboard styling
│   └── js/main.js                     # Live telemetry, map pins & chart updates
│
├── firmware/
│   ├── esp32_pothole_detector/        # ESP32 C++ Arduino firmware
│   └── arduino_uno_pothole_detector/  # Arduino Uno C++ firmware
│
├── data/
│   └── potholes.db                    # SQLite persistent database (auto-generated)
│
└── logs/
    └── email_outbox/                  # Archived HTML emails (viewable in browser)
```

---

## 🚀 Quick Start Guide

### Step 1: Run the Web Dashboard

Open your terminal in this project folder and run:

```bash
python app.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

### Step 2: Test Without Physical Hardware (Interactive Simulation)

The system includes a vehicle drive simulator so you can test and demonstrate everything immediately:

1. Click **"Start Vehicle Drive"** in the top navigation bar.
2. Watch the blue vehicle marker move along the road route on the live map.
3. Observe the live **Ultrasonic Depth** and **Z-Axis Vibration** gauges.
4. When the vehicle hits a pre-mapped or random pothole:
   - An alert banner appears on screen.
   - A color-coded marker (Red/Orange/Green) drops onto the map at the exact GPS coordinates.
   - An automated email alert is generated and dispatched!
5. Or, click the **"⚡ Trigger Pothole"** button anytime to instantly inject a Severe, Moderate, or Minor pothole at the vehicle's position.

---

### Step 3: Inspect Dispatched Email Alerts

- Click the **"Email Outbox"** button in the top navigation bar.
- Click any archived alert to open the formatted HTML email in a new tab.
- Click the **"📍 View Location in Google Maps"** button inside the email to verify the GPS coordinates directly on Google Maps!

---

## ⚙️ Enabling Live SMTP Email Delivery (e.g., Gmail)

By default, the system runs in **Safe Outbox Mode** (saving emails locally into `logs/email_outbox/` so you can test without needing email credentials).

To send live emails to an authority or your inbox:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your email details:
   ```env
   ENABLE_LIVE_EMAIL=True
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=your_email@gmail.com
   SENDER_PASSWORD=your_16_character_gmail_app_password
   RECIPIENT_EMAIL=pwd.roadmaintenance@city.gov
   ```
   *(For Gmail, generate an **App Password** via Google Account $\rightarrow$ Security $\rightarrow$ 2-Step Verification $\rightarrow$ App Passwords).*

---

## 🔌 Connecting Physical Microcontrollers (ESP32 / Arduino)

1. Connect the sensors to your ESP32 or Arduino according to [WIRING_AND_CIRCUIT_GUIDE.md](file:///c:/Users/Lenovo/OneDrive/Desktop/new/WIRING_AND_CIRCUIT_GUIDE.md).
2. Open the respective `.ino` file in the Arduino IDE:
   - For ESP32: [`firmware/esp32_pothole_detector/esp32_pothole_detector.ino`](file:///c:/Users/Lenovo/OneDrive/Desktop/new/firmware/esp32_pothole_detector/esp32_pothole_detector.ino)
   - For Arduino Uno: [`firmware/arduino_uno_pothole_detector/arduino_uno_pothole_detector.ino`](file:///c:/Users/Lenovo/OneDrive/Desktop/new/firmware/arduino_uno_pothole_detector/arduino_uno_pothole_detector.ino)
3. Upload the code to your board.
4. Connect the board via USB to your computer.
5. In `.env`, set `SERIAL_PORT=COM3` (replace with your port) and restart `app.py`. The system will automatically read incoming live sensor frames!

---

## 📊 Road Authority Management & CSV Export

- **Status Tracking:** Road authorities can change pothole statuses directly on the dashboard (*Pending* $\rightarrow$ *In Progress* $\rightarrow$ *Repaired*).
- **Data Export:** Click **"Export CSV"** to download the complete road inspection history for spreadsheet analysis or municipal GIS systems.
- **Project Report:** A comprehensive academic project report is available in [PROJECT_REPORT.md](file:///c:/Users/Lenovo/OneDrive/Desktop/new/PROJECT_REPORT.md).

