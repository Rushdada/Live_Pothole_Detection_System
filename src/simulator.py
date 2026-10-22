"""
Vehicle Simulation Module
Simulates a vehicle traveling along GPS road tracks, generating continuous
ultrasonic sensor and accelerometer telemetry with realistic road anomalies.
"""
import time
import random
import threading
from typing import Dict, Any, List, Optional
from src.detector import detector

# Realistic pre-mapped urban drive route (e.g. city boulevard loop)
SIMULATED_ROUTE: List[Dict[str, float]] = [
    {"lat": 12.971598, "lng": 77.594562, "pothole": False},
    {"lat": 12.972100, "lng": 77.595200, "pothole": False},
    {"lat": 12.972800, "lng": 77.596000, "pothole": True, "depth": 8.5, "vibration": 2.3}, # Pothole 1
    {"lat": 12.973400, "lng": 77.596800, "pothole": False},
    {"lat": 12.974100, "lng": 77.597500, "pothole": False},
    {"lat": 12.974900, "lng": 77.598300, "pothole": True, "depth": 12.0, "vibration": 2.9}, # Pothole 2 (Severe)
    {"lat": 12.975600, "lng": 77.599100, "pothole": False},
    {"lat": 12.976300, "lng": 77.599900, "pothole": False},
    {"lat": 12.977000, "lng": 77.600800, "pothole": True, "depth": 5.2, "vibration": 1.7}, # Pothole 3 (Minor)
    {"lat": 12.977800, "lng": 77.601500, "pothole": False},
    {"lat": 12.978500, "lng": 77.602300, "pothole": False},
    {"lat": 12.979200, "lng": 77.603100, "pothole": True, "depth": 9.8, "vibration": 2.6}, # Pothole 4 (Severe)
    {"lat": 12.979900, "lng": 77.604000, "pothole": False},
    {"lat": 12.980600, "lng": 77.604800, "pothole": False},
    {"lat": 12.981300, "lng": 77.605600, "pothole": False},
]

class VehicleSimulator:
    def __init__(self):
        self.is_running = False
        self.current_index = 0
        self.current_lat = SIMULATED_ROUTE[0]["lat"]
        self.current_lng = SIMULATED_ROUTE[0]["lng"]
        self.current_speed = 42.0
        self.current_depth = 20.0
        self.current_vibration = 1.0
        self.thread: Optional[threading.Thread] = None
        self.last_detected_pothole: Optional[Dict[str, Any]] = None

    def start_simulation(self, interval_sec: float = 2.0):
        """Starts background simulation loop."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, args=(interval_sec,), daemon=True)
        self.thread.start()

    def stop_simulation(self):
        """Stops the simulation loop."""
        self.is_running = False

    def _run_loop(self, interval_sec: float):
        while self.is_running:
            self.step()
            time.sleep(interval_sec)

    def step(self) -> Dict[str, Any]:
        """Advances simulation by one waypoint and returns the current telemetry frame."""
        wp = SIMULATED_ROUTE[self.current_index]
        self.current_lat = wp["lat"] + random.uniform(-0.00005, 0.00005)
        self.current_lng = wp["lng"] + random.uniform(-0.00005, 0.00005)
        self.current_speed = round(random.uniform(35.0, 50.0), 1)

        detected_event = None

        if wp.get("pothole", False):
            # Vehicle encounters a pothole!
            depth_delta = wp.get("depth", 8.0) + random.uniform(-0.5, 0.5)
            # Distance from sensor to bottom of pothole = baseline (20cm) + depth
            self.current_depth = round(20.0 + depth_delta, 1)
            self.current_vibration = round(wp.get("vibration", 2.2) + random.uniform(-0.2, 0.2), 2)

            detected_event = detector.process_sensor_reading(
                distance_cm=self.current_depth,
                vibration_g=self.current_vibration,
                latitude=self.current_lat,
                longitude=self.current_lng,
                speed_kmh=self.current_speed,
                send_email=True
            )
            if detected_event:
                self.last_detected_pothole = detected_event
        else:
            # Smooth road surface with minor normal micro-vibrations
            self.current_depth = round(20.0 + random.uniform(-0.6, 0.6), 1)
            self.current_vibration = round(1.0 + random.uniform(-0.08, 0.08), 2)
            detector.process_sensor_reading(
                distance_cm=self.current_depth,
                vibration_g=self.current_vibration,
                latitude=self.current_lat,
                longitude=self.current_lng,
                speed_kmh=self.current_speed,
                send_email=False
            )

        # Move to next waypoint
        self.current_index = (self.current_index + 1) % len(SIMULATED_ROUTE)

        return {
            "latitude": self.current_lat,
            "longitude": self.current_lng,
            "speed_kmh": self.current_speed,
            "distance_cm": self.current_depth,
            "effective_depth_cm": max(0.0, self.current_depth - 20.0),
            "vibration_g": self.current_vibration,
            "pothole_detected": detected_event is not None,
            "pothole_data": detected_event
        }

    def trigger_instant_pothole(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        severity: str = "HIGH"
    ) -> Dict[str, Any]:
        """Manually trigger a pothole event at the specified or current vehicle location."""
        target_lat = lat if lat is not None else self.current_lat + random.uniform(-0.001, 0.001)
        target_lng = lng if lng is not None else self.current_lng + random.uniform(-0.001, 0.001)

        if severity == "HIGH":
            depth_delta = random.uniform(10.5, 14.0)
            vibration = random.uniform(2.6, 3.4)
        elif severity == "MEDIUM":
            depth_delta = random.uniform(7.0, 9.5)
            vibration = random.uniform(1.9, 2.4)
        else:
            depth_delta = random.uniform(4.0, 6.5)
            vibration = random.uniform(1.4, 1.8)

        distance = 20.0 + depth_delta
        speed = round(random.uniform(30.0, 48.0), 1)

        event = detector.process_sensor_reading(
            distance_cm=distance,
            vibration_g=vibration,
            latitude=target_lat,
            longitude=target_lng,
            speed_kmh=speed,
            send_email=True
        )
        self.last_detected_pothole = event
        return event

# Global simulator instance
simulator = VehicleSimulator()

