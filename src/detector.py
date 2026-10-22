"""
Pothole Detection & Classification Engine
Processes ultrasonic depth measurements, accelerometer vibration spikes, and GPS coordinates
to detect, categorize, and trigger automated alerts for road potholes.
"""
import time
import math
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from src.config import (
    NOMINAL_GROUND_CLEARANCE_CM,
    DEPTH_THRESHOLD_MINOR_CM,
    DEPTH_THRESHOLD_MODERATE_CM,
    DEPTH_THRESHOLD_SEVERE_CM,
    VIBRATION_THRESHOLD_G,
    COOLDOWN_SECONDS,
    RECIPIENT_EMAIL
)
import src.database as db
from src.email_service import send_pothole_email

class PotholeDetector:
    def __init__(self):
        self.baseline_clearance = NOMINAL_GROUND_CLEARANCE_CM
        self.last_detection_time = 0.0
        self.last_detected_coords = (0.0, 0.0)
        # Moving average filter for adaptive ground clearance (accounts for vehicle loading)
        self.clearance_history = [NOMINAL_GROUND_CLEARANCE_CM] * 10

    def update_baseline(self, measured_distance: float) -> None:
        """Adapts baseline distance when driving on smooth surfaces."""
        # Only adapt if reading is within realistic nominal range (15cm to 30cm)
        if 15.0 <= measured_distance <= 28.0:
            self.clearance_history.append(measured_distance)
            if len(self.clearance_history) > 20:
                self.clearance_history.pop(0)
            self.baseline_clearance = sum(self.clearance_history) / len(self.clearance_history)

    def calculate_severity(self, depth_cm: float, vibration_g: float) -> Optional[str]:
        """
        Determines pothole severity based on multi-sensor criteria.
        Returns 'HIGH', 'MEDIUM', 'LOW', or None if normal road.
        """
        # Pothole must have either significant depth or notable impact vibration
        if depth_cm < DEPTH_THRESHOLD_MINOR_CM and vibration_g < VIBRATION_THRESHOLD_G:
            return None

        if depth_cm >= DEPTH_THRESHOLD_SEVERE_CM or vibration_g >= 2.6:
            return "HIGH"
        elif depth_cm >= DEPTH_THRESHOLD_MODERATE_CM or vibration_g >= 1.9:
            return "MEDIUM"
        elif depth_cm >= DEPTH_THRESHOLD_MINOR_CM or vibration_g >= VIBRATION_THRESHOLD_G:
            return "LOW"
        return None

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes distance in meters between two GPS coordinates."""
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def is_in_cooldown(self, current_lat: float, current_lng: float) -> bool:
        """Prevents duplicate logging of the same pothole within cooldown time and distance window."""
        now = time.time()
        time_elapsed = now - self.last_detection_time
        if time_elapsed < COOLDOWN_SECONDS:
            return True

        # If vehicle is within 5 meters of previous detection in the last 15 seconds
        if time_elapsed < 15.0 and self.last_detected_coords != (0.0, 0.0):
            dist = self.haversine_distance(current_lat, current_lng, self.last_detected_coords[0], self.last_detected_coords[1])
            if dist < 5.0:
                return True

        return False

    def reverse_geocode(self, lat: float, lng: float) -> str:
        """Fetches approximate street name or area via OpenStreetMap Nominatim with timeout."""
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1"
            headers = {"User-Agent": "PotholeDetectionIoT/1.0"}
            response = requests.get(url, headers=headers, timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                display_name = data.get("display_name", "")
                if display_name:
                    # Shorten to first 3 comma separated parts
                    parts = [p.strip() for p in display_name.split(",")[:3]]
                    return ", ".join(parts)
        except Exception:
            pass
        return f"Road Sector ({lat:.4f}° N, {lng:.4f}° E)"

    def process_sensor_reading(
        self,
        distance_cm: float,
        vibration_g: float,
        latitude: float,
        longitude: float,
        speed_kmh: float = 35.0,
        send_email: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Processes a single synchronized telemetry frame.
        If a pothole is confirmed:
          1. Formats pothole details
          2. Inserts into database
          3. Sends automated email alert to road maintenance authorities
          4. Returns the created record
        """
        # Validate GPS coordinate fix
        if latitude == 0.0 and longitude == 0.0:
            return None

        # Depth relative to baseline road level
        effective_depth = max(0.0, distance_cm - self.baseline_clearance)

        # Check severity
        severity = self.calculate_severity(effective_depth, vibration_g)

        if not severity:
            # Smooth road: adapt baseline
            self.update_baseline(distance_cm)
            return None

        # Check cooldown to prevent duplicate triggers
        if self.is_in_cooldown(latitude, longitude):
            return None

        now = time.time()
        self.last_detection_time = now
        self.last_detected_coords = (latitude, longitude)

        # Geocode location
        address = self.reverse_geocode(latitude, longitude)

        pothole_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "depth_cm": round(effective_depth, 1),
            "vibration_g": round(vibration_g, 2),
            "speed_kmh": round(speed_kmh, 1),
            "severity": severity,
            "address": address,
            "status": "Pending",
            "email_sent": 0,
            "email_recipient": RECIPIENT_EMAIL,
            "notes": f"Auto-detected by vehicle sensor unit (clearance baseline: {self.baseline_clearance:.1f}cm)."
        }

        # 1. Store in SQLite Database
        pothole_id = db.insert_pothole(pothole_record)
        pothole_record["id"] = pothole_id

        # 2. Dispatch Automated Email Alert
        email_result_msg = ""
        if send_email:
            success, msg = send_pothole_email(pothole_record)
            email_result_msg = msg
            if success:
                pothole_record["email_sent"] = 1

        pothole_record["email_message"] = email_result_msg
        return pothole_record

# Global detector instance
detector = PotholeDetector()

