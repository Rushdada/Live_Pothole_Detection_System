"""
Hardware Serial Telemetry Reader
Reads live sensor frames (GPS, Ultrasonic, Accelerometer) from physical microcontrollers
(ESP32, Arduino Uno/Mega) via USB Serial interface.
"""
import time
import json
import threading
import serial
import serial.tools.list_ports
from typing import Optional, Callable
from src.config import SERIAL_PORT, SERIAL_BAUD_RATE
from src.detector import detector

class HardwareSerialReader:
    def __init__(self, port: str = SERIAL_PORT, baud: int = SERIAL_BAUD_RATE):
        self.port = port
        self.baud = baud
        self.serial_conn: Optional[serial.Serial] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.on_frame_callback: Optional[Callable] = None

    @staticmethod
    def list_available_ports():
        """Lists all detectable hardware COM ports."""
        ports = serial.tools.list_ports.comports()
        return [{"device": p.device, "description": p.description} for p in ports]

    def start(self, on_frame: Optional[Callable] = None):
        """Starts the background listening thread."""
        self.on_frame_callback = on_frame
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops reading and closes the serial connection."""
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass

    def _read_loop(self):
        while self.is_running:
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    self.serial_conn = serial.Serial(self.port, self.baud, timeout=1.0)
                    print(f"[SERIAL] Connected to {self.port} at {self.baud} baud.")

                line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                frame = self.parse_line(line)
                if frame:
                    # Feed into detector
                    pothole_event = detector.process_sensor_reading(
                        distance_cm=frame.get("distance_cm", 20.0),
                        vibration_g=frame.get("vibration_g", 1.0),
                        latitude=frame.get("latitude", 0.0),
                        longitude=frame.get("longitude", 0.0),
                        speed_kmh=frame.get("speed_kmh", 0.0),
                        send_email=True
                    )
                    frame["pothole_detected"] = pothole_event is not None
                    frame["pothole_data"] = pothole_event

                    if self.on_frame_callback:
                        self.on_frame_callback(frame)

            except serial.SerialException:
                # Device might be unplugged or port busy; wait and retry
                time.sleep(3.0)
            except Exception as e:
                print(f"[SERIAL ERROR] {e}")
                time.sleep(1.0)

    def parse_line(self, line: str) -> Optional[dict]:
        """
        Parses incoming serial lines in JSON format or comma-separated format.
        JSON format: {"lat": 12.97, "lng": 77.59, "dist": 27.5, "vib": 2.4, "spd": 35.0}
        CSV format: POTHOLE_DATA,12.9716,77.5946,28.4,2.3,42.0
        """
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return {
                    "latitude": float(data.get("lat", data.get("latitude", 0.0))),
                    "longitude": float(data.get("lng", data.get("longitude", 0.0))),
                    "distance_cm": float(data.get("dist", data.get("distance_cm", 20.0))),
                    "vibration_g": float(data.get("vib", data.get("vibration_g", 1.0))),
                    "speed_kmh": float(data.get("spd", data.get("speed_kmh", 0.0)))
                }
            except Exception:
                return None

        if line.startswith("POTHOLE_DATA,"):
            parts = line.split(",")
            if len(parts) >= 6:
                try:
                    return {
                        "latitude": float(parts[1]),
                        "longitude": float(parts[2]),
                        "distance_cm": float(parts[3]),
                        "vibration_g": float(parts[4]),
                        "speed_kmh": float(parts[5])
                    }
                except ValueError:
                    return None

        return None

# Global serial reader instance
serial_reader = HardwareSerialReader()

