"""
Database Management Module
Handles SQLite schema initialization, storage, filtering, and reporting of pothole events.
"""
import sqlite3
import csv
import io
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.config import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    """Creates a database connection with dict-like row access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initializes the database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS potholes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            depth_cm REAL NOT NULL,
            vibration_g REAL NOT NULL,
            speed_kmh REAL DEFAULT 0.0,
            severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH')),
            address TEXT,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Repaired')),
            email_sent INTEGER DEFAULT 0,
            email_recipient TEXT,
            map_url TEXT,
            image_path TEXT,
            notes TEXT
        )
    """)
    # Add image_path column if upgrading existing database
    try:
        cursor.execute("ALTER TABLE potholes ADD COLUMN image_path TEXT")
    except Exception:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_potholes_timestamp ON potholes(timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_potholes_severity ON potholes(severity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_potholes_status ON potholes(status)")
    conn.commit()
    conn.close()

def insert_pothole(data: Dict[str, Any]) -> int:
    """
    Inserts a newly detected pothole record into the database.
    Returns the inserted pothole ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lat = float(data["latitude"])
    lng = float(data["longitude"])
    depth = float(data.get("depth_cm", 0.0))
    vibration = float(data.get("vibration_g", 1.0))
    speed = float(data.get("speed_kmh", 0.0))
    severity = data.get("severity", "MEDIUM")
    address = data.get("address", f"Near Lat: {lat:.5f}, Lng: {lng:.5f}")
    status = data.get("status", "Pending")
    email_sent = int(data.get("email_sent", 0))
    email_recipient = data.get("email_recipient", "")
    map_url = f"https://www.google.com/maps?q={lat},{lng}"
    image_path = data.get("image_path", "")
    notes = data.get("notes", "")

    cursor.execute("""
        INSERT INTO potholes (
            timestamp, latitude, longitude, depth_cm, vibration_g,
            speed_kmh, severity, address, status, email_sent,
            email_recipient, map_url, image_path, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, lat, lng, depth, vibration,
        speed, severity, address, status, email_sent,
        email_recipient, map_url, image_path, notes
    ))
    
    pothole_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pothole_id

def get_all_potholes(
    limit: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves potholes with optional filtering."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM potholes WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)

    query += " ORDER BY id DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_pothole_by_id(pothole_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single pothole by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM potholes WHERE id = ?", (pothole_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_pothole_status(pothole_id: int, new_status: str, notes: Optional[str] = None) -> bool:
    """Updates the repair/inspection status of a pothole."""
    conn = get_connection()
    cursor = conn.cursor()
    if notes is not None:
        cursor.execute("""
            UPDATE potholes
            SET status = ?, notes = ?
            WHERE id = ?
        """, (new_status, notes, pothole_id))
    else:
        cursor.execute("""
            UPDATE potholes
            SET status = ?
            WHERE id = ?
        """, (new_status, pothole_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def mark_email_sent(pothole_id: int, recipient: str) -> bool:
    """Marks a pothole record as having had an email alert sent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE potholes
        SET email_sent = 1, email_recipient = ?
        WHERE id = ?
    """, (recipient, pothole_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_statistics() -> Dict[str, Any]:
    """Computes summary statistics for dashboard metrics and road safety analysis."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM potholes")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE severity = 'HIGH'")
    high = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE severity = 'MEDIUM'")
    medium = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE severity = 'LOW'")
    low = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE status = 'Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE status = 'In Progress'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE status = 'Repaired'")
    repaired = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM potholes WHERE email_sent = 1")
    emails_sent = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(depth_cm) FROM potholes")
    avg_depth = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT AVG(vibration_g) FROM potholes")
    avg_vibration = cursor.fetchone()[0] or 0.0

    conn.close()

    return {
        "total": total,
        "high_severity": high,
        "medium_severity": medium,
        "low_severity": low,
        "pending": pending,
        "in_progress": in_progress,
        "repaired": repaired,
        "emails_sent": emails_sent,
        "avg_depth_cm": round(avg_depth, 2),
        "avg_vibration_g": round(avg_vibration, 2)
    }

def export_to_csv() -> str:
    """Exports all pothole records to a CSV string."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM potholes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    if rows:
        headers = rows[0].keys()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))
    else:
        output.write("id,timestamp,latitude,longitude,depth_cm,vibration_g,speed_kmh,severity,address,status,email_sent,email_recipient,map_url,notes\n")

    return output.getvalue()

def clear_all() -> None:
    """Clears all records from the potholes table (useful for demonstrations/resets)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM potholes")
    conn.commit()
    conn.close()

