"""
Email Alert Dispatcher Module
Constructs and dispatches responsive HTML email notifications containing pothole severity,
exact GPS coordinates, sensor telemetry, live camera snapshots, and direct Google Maps navigation links.
"""
import os
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from typing import Dict, Any, Tuple
from pathlib import Path

from src.config import (
    SMTP_SERVER,
    SMTP_PORT,
    SENDER_EMAIL,
    SENDER_PASSWORD,
    RECIPIENT_EMAIL,
    ENABLE_LIVE_EMAIL,
    EMAIL_OUTBOX_DIR
)
import src.database as db

def generate_email_html(pothole: Dict[str, Any]) -> str:
    """Generates an HTML email alert template with embedded camera snapshot if available."""
    severity = pothole.get("severity", "MEDIUM").upper()
    lat = pothole.get("latitude", 0.0)
    lng = pothole.get("longitude", 0.0)
    depth = pothole.get("depth_cm", 0.0)
    vibration = pothole.get("vibration_g", 0.0)
    speed = pothole.get("speed_kmh", 0.0)
    timestamp = pothole.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    pothole_id = pothole.get("id", "N/A")
    address = pothole.get("address", f"Lat: {lat:.6f}, Lng: {lng:.6f}")
    google_maps_url = f"https://www.google.com/maps?q={lat},{lng}"
    image_path = pothole.get("image_path")

    # Severity styling
    if severity == "HIGH":
        color_badge = "#dc2626"
        badge_bg = "#fee2e2"
        badge_text = "#991b1b"
        header_color = "#b91c1c"
        urgency_msg = "URGENT ATTENTION REQUIRED: Severe hazard detected, vehicle damage/accident risk."
    elif severity == "MEDIUM":
        color_badge = "#ea580c"
        badge_bg = "#ffedd5"
        badge_text = "#9a3412"
        header_color = "#c2410c"
        urgency_msg = "PRIORITY MAINTENANCE: Moderate pothole detected. Schedule repair."
    else:
        color_badge = "#16a34a"
        badge_bg = "#dcfce7"
        badge_text = "#166534"
        header_color = "#15803d"
        urgency_msg = "ROUTINE MONITORING: Minor surface depression recorded."

    # Embedded camera snapshot HTML
    image_html = ""
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                b64_img = base64.b64encode(img_file.read()).decode("utf-8")
                image_html = f"""
                <div style="margin: 22px 0 16px 0; text-align: center;">
                    <div style="font-size: 13px; font-weight: 700; color: #475569; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">
                        📸 Live Mobile Camera Pothole Capture
                    </div>
                    <img src="data:image/jpeg;base64,{b64_img}" style="max-width: 100%; height: auto; border-radius: 8px; border: 2px solid #cbd5e1; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);" alt="Pothole Live Snapshot" />
                </div>
                """
        except Exception:
            image_html = ""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pothole Alert - ID #{pothole_id}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 30px 10px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {header_color}; padding: 24px; text-align: center; color: #ffffff;">
                            <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">
                                ⚠️ ROAD HAZARD ALERT
                            </h1>
                            <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.95;">
                                Mobile Camera & IoT Pothole Geolocation Reporting System
                            </p>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 28px;">
                            <div style="background-color: {badge_bg}; border-left: 4px solid {color_badge}; padding: 12px 16px; border-radius: 4px; margin-bottom: 24px;">
                                <strong style="color: {badge_text}; font-size: 15px;">{urgency_msg}</strong>
                            </div>

                            <table width="100%" cellpadding="8" cellspacing="0" style="margin-bottom: 20px; border-collapse: collapse;">
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td width="35%" style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Incident ID</td>
                                    <td style="font-size: 15px; font-weight: 700; color: #0f172a;">#{pothole_id}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Severity Level</td>
                                    <td>
                                        <span style="background-color: {color_badge}; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700;">
                                            {severity}
                                        </span>
                                    </td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Timestamp</td>
                                    <td style="font-size: 14px; color: #334155;">{timestamp}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">GPS Coordinates</td>
                                    <td style="font-size: 14px; font-family: monospace; color: #0f172a; font-weight: 600;">
                                        {lat:.6f}° N, {lng:.6f}° E
                                    </td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Approx. Location</td>
                                    <td style="font-size: 14px; color: #334155;">{address}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Estimated Depth</td>
                                    <td style="font-size: 14px; font-weight: 600; color: #0f172a;">{depth:.1f} cm</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Impact Shock</td>
                                    <td style="font-size: 14px; font-weight: 600; color: #0f172a;">{vibration:.2f} g</td>
                                </tr>
                                <tr>
                                    <td style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Vehicle Speed</td>
                                    <td style="font-size: 14px; color: #334155;">{speed:.1f} km/h</td>
                                </tr>
                            </table>

                            <!-- Live Camera Snapshot Embed -->
                            {image_html}

                            <!-- Google Maps Direct CTA -->
                            <div style="text-align: center; margin: 26px 0 16px 0;">
                                <a href="{google_maps_url}" target="_blank" style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.4);">
                                    📍 View Location in Google Maps
                                </a>
                            </div>
                            <p style="text-align: center; font-size: 12px; color: #94a3b8; margin: 0;">
                                Direct Link: <a href="{google_maps_url}" style="color: #2563eb;">{google_maps_url}</a>
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 20px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #64748b;">
                            <p style="margin: 0 0 6px 0;">
                                Alert dispatched automatically to <strong>{RECIPIENT_EMAIL}</strong>.
                            </p>
                            <p style="margin: 0;">
                                Municipal Pothole Detection & Mobile Camera System
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

def generate_plain_text(pothole: Dict[str, Any]) -> str:
    """Generates a plain-text fallback version of the alert."""
    lat = pothole.get("latitude", 0.0)
    lng = pothole.get("longitude", 0.0)
    google_maps_url = f"https://www.google.com/maps?q={lat},{lng}"

    return f"""*** ROAD HAZARD ALERT: POTHOLE DETECTED ***
--------------------------------------------------
Incident ID    : #{pothole.get('id', 'N/A')}
Severity       : {pothole.get('severity', 'UNKNOWN')}
Timestamp      : {pothole.get('timestamp', '')}
Latitude       : {lat:.6f}
Longitude      : {lng:.6f}
Depth          : {pothole.get('depth_cm', 0.0)} cm
Impact Force   : {pothole.get('vibration_g', 0.0)} g
Vehicle Speed  : {pothole.get('speed_kmh', 0.0)} km/h
Google Maps    : {google_maps_url}
--------------------------------------------------
Recipient      : {RECIPIENT_EMAIL}
Automated alert from Mobile Camera Pothole Detection System.
"""

def send_pothole_email(pothole: Dict[str, Any], recipient: str = None) -> Tuple[bool, str]:
    """
    Sends an email alert to rushipapu456@gmail.com (or custom recipient).
    If ENABLE_LIVE_EMAIL is True and credentials are provided, connects via SMTP.
    Otherwise (or if SMTP fails), saves the generated HTML email into logs/email_outbox/
    and returns a simulation success message with the file path.
    """
    recipient_email = recipient or RECIPIENT_EMAIL
    pothole_id = pothole.get("id", "new")
    severity = pothole.get("severity", "MEDIUM")
    subject = f"🚨 [ROAD ALERT] {severity} Severity Pothole Detected (ID #{pothole_id})"
    image_path = pothole.get("image_path")

    html_content = generate_email_html(pothole)
    text_content = generate_plain_text(pothole)

    # 1. Attempt Live SMTP if configured
    if ENABLE_LIVE_EMAIL and SENDER_PASSWORD and SENDER_EMAIL:
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = f"Pothole Alert System <{SENDER_EMAIL}>"
            msg["To"] = recipient_email

            alt_part = MIMEMultipart("alternative")
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            alt_part.attach(part1)
            alt_part.attach(part2)
            msg.attach(alt_part)

            # Attach camera snapshot if present
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as f:
                        img_attachment = MIMEImage(f.read())
                        img_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                        msg.attach(img_attachment)
                except Exception:
                    pass

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, [recipient_email], msg.as_string())

            if isinstance(pothole_id, int):
                db.mark_email_sent(pothole_id, recipient_email)

            return True, f"Live email successfully sent to {recipient_email}"
        except Exception as e:
            fallback_err = str(e)
    else:
        fallback_err = f"Live SMTP not configured (ENABLE_LIVE_EMAIL={ENABLE_LIVE_EMAIL}). Saved to local Outbox."

    # 2. Local Outbox Simulation (Saves readable HTML for testing & inspection)
    try:
        Path(EMAIL_OUTBOX_DIR).mkdir(parents=True, exist_ok=True)
        filename = f"alert_pothole_{pothole_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        file_path = os.path.join(EMAIL_OUTBOX_DIR, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        if isinstance(pothole_id, int):
            db.mark_email_sent(pothole_id, recipient_email)

        return True, f"Alert saved to outbox for {recipient_email}: {os.path.basename(file_path)}"
    except Exception as e:
        return False, f"Failed to save to outbox: {str(e)}"
