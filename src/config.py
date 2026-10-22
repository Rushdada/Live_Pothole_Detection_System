"""
System Configuration Module
Handles environment variables, default thresholds, email settings, and paths.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if available
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "potholes.db"))

# Email Alert Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "alert.potholedetector@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")  # App-specific password for Gmail
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "rushipapu456@gmail.com")
ENABLE_LIVE_EMAIL = os.getenv("ENABLE_LIVE_EMAIL", "False").lower() in ("true", "1", "yes")

# Outbox directory for saving emails locally when live email is disabled or during testing
EMAIL_OUTBOX_DIR = str(BASE_DIR / "logs" / "email_outbox")

# Hardware / Serial Port Configuration
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
SERIAL_BAUD_RATE = int(os.getenv("SERIAL_BAUD_RATE", 115200))

# Pothole Detection Thresholds
NOMINAL_GROUND_CLEARANCE_CM = float(os.getenv("NOMINAL_GROUND_CLEARANCE_CM", 20.0))  # Vehicle clearance
DEPTH_THRESHOLD_MINOR_CM = float(os.getenv("DEPTH_THRESHOLD_MINOR_CM", 4.0))       # Drop >= 4cm
DEPTH_THRESHOLD_MODERATE_CM = float(os.getenv("DEPTH_THRESHOLD_MODERATE_CM", 7.0)) # Drop >= 7cm
DEPTH_THRESHOLD_SEVERE_CM = float(os.getenv("DEPTH_THRESHOLD_SEVERE_CM", 10.0))     # Drop >= 10cm

VIBRATION_THRESHOLD_G = float(os.getenv("VIBRATION_THRESHOLD_G", 1.6))              # Vertical Z acceleration spike (1g = normal gravity)
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", 3.0))                         # Avoid multiple detections for single pothole

# Web Server Configuration
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", 5000)))
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "yes")

