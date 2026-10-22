"""
Computer Vision Pothole Detector Module
Processes mobile camera frames, detects road surface anomalies/potholes using
OpenCV contour & dark cavity segmentation, annotates bounding boxes, and triggers email alerts.
"""
import os
import cv2
import base64
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from src.config import RECIPIENT_EMAIL, BASE_DIR
import src.database as db
from src.email_service import send_pothole_email

SNAPSHOTS_DIR = str(BASE_DIR / "data" / "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

class VisionPotholeDetector:
    def __init__(self):
        self.last_detection_time = 0.0

    @staticmethod
    def decode_base64_image(b64_string: str) -> Optional[np.ndarray]:
        """Converts incoming browser canvas base64 image data into an OpenCV BGR image."""
        try:
            if "," in b64_string:
                b64_string = b64_string.split(",")[1]
            img_bytes = base64.b64decode(b64_string)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[VISION ERROR] Failed to decode image: {e}")
            return None

    def analyze_frame(
        self,
        img: np.ndarray,
        sensitivity: float = 0.5,
        force_detect: bool = False
    ) -> Tuple[bool, Optional[Tuple[int, int, int, int]], str, float]:
        """
        Analyzes road surface in frame.
        Returns: (detected, bbox (x,y,w,h), severity, estimated_depth_cm)
        """
        h, w = img.shape[:2]

        # 1. Focus on Road Region of Interest (ROI) - bottom 65% of the camera frame
        roi_top = int(h * 0.35)
        roi = img[roi_top:h, 0:w]

        # 2. Convert to Grayscale & apply contrast enhancement (CLAHE)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 3. Gaussian Blur to reduce pavement gravel noise
        blurred = cv2.GaussianBlur(enhanced, (9, 9), 0)

        # 4. Adaptive thresholding to segment dark road cavities/shadows
        # Sensitivity adjusts threshold sensitivity
        block_size = 25
        c_val = int(7 * (1.2 - sensitivity))
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, block_size, c_val
        )

        # 5. Morphological closing to fill small gaps inside pothole cavities
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        # 6. Find contours of potential potholes
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_bbox = None
        max_area = 0
        min_area = int((w * h) * 0.015) # Minimum 1.5% of frame area

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect_ratio = float(bw) / bh
                # Potholes are typically roughly elliptical (aspect ratio 0.4 to 2.8)
                if 0.4 <= aspect_ratio <= 2.8 and area > max_area:
                    max_area = area
                    best_bbox = (x, y + roi_top, bw, bh)

        # If a pothole candidate was found
        if best_bbox is not None:
            area_ratio = max_area / (w * h)
            if area_ratio > 0.08:
                severity = "HIGH"
                est_depth = round(10.0 + min(15.0, area_ratio * 40), 1)
            elif area_ratio > 0.035:
                severity = "MEDIUM"
                est_depth = round(7.0 + (area_ratio * 25), 1)
            else:
                severity = "LOW"
                est_depth = round(4.0 + (area_ratio * 15), 1)
            return True, best_bbox, severity, est_depth

        # If forced simulation / manual capture trigger was pressed
        if force_detect:
            # Generate a center-road detection bounding box
            bw = int(w * 0.42)
            bh = int(h * 0.30)
            bx = int(w * 0.29)
            by = int(h * 0.48)
            return True, (bx, by, bw, bh), "HIGH", 11.5

        return False, None, "LOW", 0.0

    def process_camera_frame(
        self,
        b64_image: str,
        latitude: float,
        longitude: float,
        speed_kmh: float = 35.0,
        sensitivity: float = 0.5,
        force_detect: bool = False,
        recipient: str = RECIPIENT_EMAIL
    ) -> Dict[str, Any]:
        """
        Receives camera snapshot from mobile device, detects potholes,
        annotates the frame with red hazard bounding boxes & telemetry,
        saves the image, and sends real-time email alert to rushipapu456@gmail.com.
        """
        img = self.decode_base64_image(b64_image)
        if img is None:
            return {"success": False, "detected": False, "error": "Invalid camera frame"}

        detected, bbox, severity, depth_cm = self.analyze_frame(
            img, sensitivity=sensitivity, force_detect=force_detect
        )

        if not detected:
            return {
                "success": True,
                "detected": False,
                "message": "Scanning active. Road surface clear."
            }

        x, y, w, h = bbox
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Color based on severity (BGR format for OpenCV)
        box_color = (0, 0, 235) if severity == "HIGH" else ((0, 140, 255) if severity == "MEDIUM" else (0, 180, 0))

        # 1. Draw Bounding Box around pothole
        cv2.rectangle(img, (x, y), (x + w, y + h), box_color, 3)

        # 2. Draw Top Tag / Severity Header
        tag_text = f"POTHOLE DETECTED: {severity} ({depth_cm}cm)"
        (text_w, text_h), baseline = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(img, (x, y - text_h - 10), (x + text_w + 10, y), box_color, -1)
        cv2.putText(img, tag_text, (x + 5, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        # 3. Draw Watermark Header at top of image
        cv2.rectangle(img, (0, 0), (img.shape[1], 44), (20, 20, 20), -1)
        gps_info = f"GPS: {latitude:.6f} N, {longitude:.6f} E | Speed: {speed_kmh:.1f} km/h | {timestamp_str}"
        cv2.putText(img, gps_info, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 1, cv2.LINE_AA)

        # 4. Save annotated image to data/snapshots/
        filename = f"pothole_{file_timestamp}.jpg"
        full_filepath = os.path.join(SNAPSHOTS_DIR, filename)
        cv2.imwrite(full_filepath, img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

        # 5. Insert Record into SQLite Database
        pothole_record = {
            "timestamp": timestamp_str,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "depth_cm": depth_cm,
            "vibration_g": round(2.5 if severity == "HIGH" else (1.9 if severity == "MEDIUM" else 1.5), 2),
            "speed_kmh": round(speed_kmh, 1),
            "severity": severity,
            "address": f"Road Segment near Lat: {latitude:.5f}, Lng: {longitude:.5f}",
            "status": "Pending",
            "email_sent": 0,
            "email_recipient": recipient,
            "image_path": full_filepath,
            "notes": f"Captured live via Mobile Camera AI Scanner. Severity: {severity}."
        }
        pothole_id = db.insert_pothole(pothole_record)
        pothole_record["id"] = pothole_id

        # 6. Dispatch Email Alert immediately to rushipapu456@gmail.com
        success, email_msg = send_pothole_email(pothole_record, recipient=recipient)
        if success:
            pothole_record["email_sent"] = 1

        return {
            "success": True,
            "detected": True,
            "pothole": pothole_record,
            "bbox": {"x": x, "y": y, "width": w, "height": h},
            "image_url": f"/snapshots/{filename}",
            "email_message": email_msg
        }

# Global vision detector instance
vision_detector = VisionPotholeDetector()

