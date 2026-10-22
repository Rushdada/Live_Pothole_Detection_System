"""
Pothole Detection & Geolocation Web Server
Flask REST API, Leaflet Dashboard, and Mobile Camera AI Scanner.
"""
import os
import socket
import io
import base64
import qrcode
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from src.config import (
    WEB_HOST,
    WEB_PORT,
    DEBUG_MODE,
    RECIPIENT_EMAIL,
    ENABLE_LIVE_EMAIL,
    SENDER_EMAIL,
    SMTP_SERVER,
    EMAIL_OUTBOX_DIR,
    BASE_DIR
)
import src.database as db
from src.detector import detector
from src.simulator import simulator
from src.serial_reader import serial_reader
from src.email_service import send_pothole_email
from src.vision_detector import vision_detector, SNAPSHOTS_DIR

app = Flask(__name__, template_folder="templates", static_folder="static")

# Ensure database is initialized on startup
db.init_db()

def get_local_ip() -> str:
    """Finds the local network IP so mobile phones on the same Wi-Fi can connect."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_mobile_qr_b64(url: str) -> str:
    """Generates a base64 encoded PNG QR code for mobile navigation."""
    try:
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print(f"[QR ERROR] {e}")
        return ""

@app.route("/")
def index():
    """Renders the desktop command center dashboard."""
    return render_template("index.html")

@app.route("/mobile")
def mobile_app():
    """Renders the mobile camera pothole scanner application."""
    return render_template("mobile.html")

# ----------------- MOBILE CAMERA AI DETECTION -----------------

@app.route("/api/detect_camera_frame", methods=["POST"])
def detect_camera_frame():
    """
    Receives camera frame from mobile app, detects potholes using computer vision,
    annotates the snapshot, logs the event, and sends real-time email alert to rushipapu456@gmail.com.
    """
    payload = request.get_json() or {}
    b64_image = payload.get("image")
    if not b64_image:
        return jsonify({"success": False, "error": "No image data provided"}), 400

    lat = float(payload.get("latitude", 12.971598))
    lng = float(payload.get("longitude", 77.594562))
    speed = float(payload.get("speed_kmh", 35.0))
    sensitivity = float(payload.get("sensitivity", 0.5))
    force_detect = bool(payload.get("force_detect", False))
    recipient = payload.get("recipient") or RECIPIENT_EMAIL

    result = vision_detector.process_camera_frame(
        b64_image=b64_image,
        latitude=lat,
        longitude=lng,
        speed_kmh=speed,
        sensitivity=sensitivity,
        force_detect=force_detect,
        recipient=recipient
    )

    return jsonify(result)

@app.route("/snapshots/<path:filename>")
def get_snapshot(filename):
    """Serves annotated pothole snapshots."""
    return send_from_directory(SNAPSHOTS_DIR, filename)

# ----------------- POTHOLE CRUD & ACTIONS -----------------

@app.route("/api/potholes", methods=["GET"])
def get_potholes():
    """Retrieves all potholes with optional filtering."""
    status = request.args.get("status")
    severity = request.args.get("severity")
    limit = request.args.get("limit", type=int)
    potholes = db.get_all_potholes(limit=limit, status=status, severity=severity)
    return jsonify({"success": True, "count": len(potholes), "data": potholes})

@app.route("/api/potholes/<int:pothole_id>", methods=["GET"])
def get_pothole(pothole_id: int):
    """Retrieves a single pothole by ID."""
    pothole = db.get_pothole_by_id(pothole_id)
    if not pothole:
        return jsonify({"success": False, "error": "Pothole not found"}), 404
    return jsonify({"success": True, "data": pothole})

@app.route("/api/potholes/<int:pothole_id>/status", methods=["PUT"])
def update_status(pothole_id: int):
    """Updates the status (Pending / In Progress / Repaired) of a pothole."""
    payload = request.get_json() or {}
    new_status = payload.get("status")
    notes = payload.get("notes")

    if new_status not in ["Pending", "In Progress", "Repaired"]:
        return jsonify({"success": False, "error": "Invalid status value"}), 400

    updated = db.update_pothole_status(pothole_id, new_status, notes)
    if not updated:
        return jsonify({"success": False, "error": "Pothole not found"}), 404

    return jsonify({"success": True, "message": f"Status updated to '{new_status}'"})

@app.route("/api/potholes/<int:pothole_id>/email", methods=["POST"])
def send_email_for_pothole(pothole_id: int):
    """Sends or resends an email alert for a specific pothole."""
    pothole = db.get_pothole_by_id(pothole_id)
    if not pothole:
        return jsonify({"success": False, "error": "Pothole not found"}), 404

    payload = request.get_json() or {}
    recipient = payload.get("recipient") or RECIPIENT_EMAIL

    success, message = send_pothole_email(pothole, recipient=recipient)
    return jsonify({"success": success, "message": message})

@app.route("/api/potholes/clear", methods=["POST"])
def clear_all_potholes():
    """Clears all records for demonstration resets."""
    db.clear_all()
    return jsonify({"success": True, "message": "All pothole records cleared."})

# ----------------- ANALYTICS & EXPORTS -----------------

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Returns aggregated summary metrics for UI cards and charts."""
    stats = db.get_statistics()
    return jsonify({"success": True, "stats": stats})

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Generates and downloads a CSV export of road hazard records."""
    csv_data = db.export_to_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=potholes_export.csv"}
    )

# ----------------- SIMULATION CONTROLS -----------------

@app.route("/api/simulation/start", methods=["POST"])
def start_sim():
    """Starts continuous background vehicle simulation."""
    interval = request.json.get("interval", 2.0) if request.is_json else 2.0
    simulator.start_simulation(interval_sec=float(interval))
    return jsonify({"success": True, "message": "Simulation started."})

@app.route("/api/simulation/stop", methods=["POST"])
def stop_sim():
    """Stops the vehicle simulation."""
    simulator.stop_simulation()
    return jsonify({"success": True, "message": "Simulation stopped."})

@app.route("/api/simulation/status", methods=["GET"])
def get_sim_status():
    """Fetches current live vehicle coordinates, speed, and sensor readings."""
    return jsonify({
        "success": True,
        "is_running": simulator.is_running,
        "telemetry": {
            "latitude": simulator.current_lat,
            "longitude": simulator.current_lng,
            "speed_kmh": simulator.current_speed,
            "distance_cm": simulator.current_depth,
            "effective_depth_cm": max(0.0, simulator.current_depth - 20.0),
            "vibration_g": simulator.current_vibration,
            "last_pothole": simulator.last_detected_pothole
        }
    })

@app.route("/api/simulation/trigger", methods=["POST"])
def trigger_sim_pothole():
    """Manually injects an instant pothole incident at selected or random coordinates."""
    payload = request.get_json() or {}
    severity = payload.get("severity", "HIGH")
    lat = payload.get("latitude")
    lng = payload.get("longitude")

    event = simulator.trigger_instant_pothole(
        lat=float(lat) if lat is not None else None,
        lng=float(lng) if lng is not None else None,
        severity=severity
    )

    return jsonify({"success": True, "pothole": event})

# ----------------- HARDWARE SERIAL & CONFIG -----------------

@app.route("/api/hardware/ports", methods=["GET"])
def get_serial_ports():
    """Lists detectable USB COM ports on host."""
    ports = serial_reader.list_available_ports()
    return jsonify({"success": True, "ports": ports})

@app.route("/api/config", methods=["GET"])
def get_current_config():
    """Returns current active system configuration."""
    return jsonify({
        "success": True,
        "config": {
            "smtp_server": SMTP_SERVER,
            "sender_email": SENDER_EMAIL,
            "recipient_email": RECIPIENT_EMAIL,
            "live_email_enabled": ENABLE_LIVE_EMAIL,
            "serial_port": serial_reader.port,
            "serial_baud": serial_reader.baud
        }
    })

@app.route("/api/server_info", methods=["GET"])
def get_server_info():
    """Returns local IP, mobile app URL, and QR code for easy smartphone connection."""
    local_ip = get_local_ip()
    port = WEB_PORT
    mobile_url = f"http://{local_ip}:{port}/mobile"
    qr_b64 = get_mobile_qr_b64(mobile_url)
    return jsonify({
        "success": True,
        "local_ip": local_ip,
        "port": port,
        "mobile_url": mobile_url,
        "qr_code_b64": qr_b64,
        "recipient_email": RECIPIENT_EMAIL
    })

# ----------------- EMAIL OUTBOX VIEWER -----------------

@app.route("/api/outbox", methods=["GET"])
def list_outbox_emails():
    """Lists saved emails in the local outbox directory."""
    if not os.path.exists(EMAIL_OUTBOX_DIR):
        return jsonify({"success": True, "emails": []})

    files = sorted(os.listdir(EMAIL_OUTBOX_DIR), reverse=True)
    html_files = [f for f in files if f.endswith(".html")]
    return jsonify({"success": True, "emails": html_files})

@app.route("/outbox/<path:filename>")
def view_outbox_email(filename):
    """Serves an archived email HTML file directly for browser inspection."""
    return send_from_directory(EMAIL_OUTBOX_DIR, filename)

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 65)
    print("🚀 Pothole Detection & Geolocation System")
    print(f"💻 Desktop Dashboard: http://127.0.0.1:{WEB_PORT}")
    print(f"📱 Mobile Application: http://{local_ip}:{WEB_PORT}/mobile")
    print(f"📧 Alert Target Email: {RECIPIENT_EMAIL}")
    print("=" * 65)
    # Listen on 0.0.0.0 so phones on the same Wi-Fi network can connect
    app.run(host="0.0.0.0", port=WEB_PORT, debug=DEBUG_MODE)
