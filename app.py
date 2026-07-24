"""
Full-Stack Automated System Monitoring & IT Asset Management Platform
------------------------------------------------------------------------
Author : Aditya Kumar
Email  : agile.aditya.kumar@gmail.com
------------------------------------------------------------------------
A lightweight Flask application that:
  1. Monitors live system resources (CPU, RAM, Disk, Network, Uptime)
  2. Automatically raises + logs alerts when usage crosses a threshold
  3. Manages an IT asset inventory (laptops, desktops, servers, etc.)
     with full CRUD support, backed by SQLite.
  4. Includes comprehensive error handling and input validation
"""

import sqlite3
import datetime
import time
import psutil
import logging
from flask import Flask, jsonify, request, g, render_template
from functools import wraps

# ======================== Logging Setup ========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
DATABASE = "asset_management.db"

# ---------------------- Alert Thresholds (%) ----------------------
CPU_THRESHOLD = 80
RAM_THRESHOLD = 80
DISK_THRESHOLD = 90
ALERT_COOLDOWN = 300  # 5 minutes between duplicate alerts

# ---------------------- Alert Cooldown Tracking ----------------------
LAST_ALERT_TIME = {"cpu": 0, "ram": 0, "disk": 0}


# ============================== Database Helpers ==============================
def get_db():
    """Get or create database connection for the current request."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at the end of request."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database with required tables (idempotent)."""
    with app.app_context():
        try:
            db = get_db()
            db.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_name TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    owner TEXT,
                    status TEXT DEFAULT 'Active',
                    location TEXT,
                    purchase_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    is_acknowledged INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise


# ============================== Validation Helpers ==============================
def validate_purchase_date(date_str):
    """Validate purchase date format (YYYY-MM-DD)."""
    if not date_str:
        return True  # Optional field
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_asset_data(data):
    """Validate required fields and data types for assets."""
    errors = []
    
    if not data:
        return ["Request body is required"]
    
    if not data.get("asset_name") or not isinstance(data.get("asset_name"), str):
        errors.append("asset_name is required and must be a string")
    
    if not data.get("asset_type") or not isinstance(data.get("asset_type"), str):
        errors.append("asset_type is required and must be a string")
    
    if data.get("asset_name") and len(data.get("asset_name", "")) > 255:
        errors.append("asset_name must not exceed 255 characters")
    
    if data.get("owner") and len(data.get("owner", "")) > 255:
        errors.append("owner must not exceed 255 characters")
    
    if data.get("purchase_date") and not validate_purchase_date(data.get("purchase_date")):
        errors.append("purchase_date must be in YYYY-MM-DD format")
    
    valid_statuses = ["Active", "Inactive", "Maintenance", "Retired"]
    if data.get("status") and data.get("status") not in valid_statuses:
        errors.append(f"status must be one of: {', '.join(valid_statuses)}")
    
    return errors


def error_handler(f):
    """Decorator for consistent error handling in API routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}")
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
    return decorated_function


# ============================== Frontend Route ==============================
@app.route("/")
def index():
    return render_template("index.html")


# ============================== System Monitoring API ==============================
@app.route("/api/system-stats")
@error_handler
def system_stats():
    """Get live system statistics and check for alerts."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = str(datetime.datetime.now() - boot_time).split(".")[0]

        stats = {
            "cpu_percent": round(cpu, 2),
            "ram_percent": round(ram.percent, 2),
            "ram_used_gb": round(ram.used / (1024 ** 3), 2),
            "ram_total_gb": round(ram.total / (1024 ** 3), 2),
            "disk_percent": round(disk.percent, 2),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "network_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
            "network_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
            "uptime": uptime,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        }

        check_and_log_alerts(stats)
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return jsonify({"error": "Failed to retrieve system statistics"}), 500


def check_and_log_alerts(stats):
    """
    Check system stats against thresholds and log alerts with cooldown.
    Prevents alert spam by enforcing ALERT_COOLDOWN between duplicate alerts.
    """
    try:
        db = get_db()
        now = time.time()
        triggered = []

        if stats["cpu_percent"] >= CPU_THRESHOLD:
            if now - LAST_ALERT_TIME["cpu"] > ALERT_COOLDOWN:
                triggered.append((
                    f"High CPU usage detected: {stats['cpu_percent']}%",
                    "Critical"
                ))
                LAST_ALERT_TIME["cpu"] = now

        if stats["ram_percent"] >= RAM_THRESHOLD:
            if now - LAST_ALERT_TIME["ram"] > ALERT_COOLDOWN:
                triggered.append((
                    f"High RAM usage detected: {stats['ram_percent']}%",
                    "Warning"
                ))
                LAST_ALERT_TIME["ram"] = now

        if stats["disk_percent"] >= DISK_THRESHOLD:
            if now - LAST_ALERT_TIME["disk"] > ALERT_COOLDOWN:
                triggered.append((
                    f"Low disk space: {stats['disk_percent']}% used",
                    "Critical"
                ))
                LAST_ALERT_TIME["disk"] = now

        for message, severity in triggered:
            db.execute(
                "INSERT INTO alerts (message, severity, created_at) VALUES (?, ?, ?)",
                (message, severity, datetime.datetime.now().isoformat())
            )
            logger.warning(f"[{severity}] {message}")

        if triggered:
            db.commit()
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")


# ============================== Alerts API ==============================
@app.route("/api/alerts")
@error_handler
def get_alerts():
    """Get last 20 system alerts."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        
        if page < 1 or per_page < 1 or per_page > 100:
            return jsonify({"error": "Invalid pagination parameters"}), 400
        
        offset = (page - 1) * per_page
        db = get_db()
        
        rows = db.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        
        total = db.execute("SELECT COUNT(*) as c FROM alerts").fetchone()["c"]
        
        return jsonify({
            "alerts": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page
        }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve alerts: {e}")
        return jsonify({"error": "Failed to retrieve alerts"}), 500


# ============================== IT Asset Management API (CRUD) ==============================
@app.route("/api/assets", methods=["GET"])
@error_handler
def get_assets():
    """Get all IT assets with optional pagination and filtering."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        status_filter = request.args.get("status", None, type=str)
        
        if page < 1 or per_page < 1 or per_page > 100:
            return jsonify({"error": "Invalid pagination parameters"}), 400
        
        offset = (page - 1) * per_page
        db = get_db()
        
        if status_filter:
            rows = db.execute(
                "SELECT * FROM assets WHERE status=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (status_filter, per_page, offset)
            ).fetchall()
            total = db.execute(
                "SELECT COUNT(*) as c FROM assets WHERE status=?",
                (status_filter,)
            ).fetchone()["c"]
        else:
            rows = db.execute(
                "SELECT * FROM assets ORDER BY id DESC LIMIT ? OFFSET ?",
                (per_page, offset)
            ).fetchall()
            total = db.execute(
                "SELECT COUNT(*) as c FROM assets"
            ).fetchone()["c"]
        
        return jsonify({
            "assets": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page
        }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve assets: {e}")
        return jsonify({"error": "Failed to retrieve assets"}), 500


@app.route("/api/assets", methods=["POST"])
@error_handler
def add_asset():
    """Add a new IT asset with validation."""
    try:
        data = request.get_json()
        
        # Validate input
        errors = validate_asset_data(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        db = get_db()
        db.execute(
            """INSERT INTO assets (asset_name, asset_type, owner, status, location, purchase_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("asset_name").strip(),
                data.get("asset_type").strip(),
                data.get("owner", "").strip() or None,
                data.get("status", "Active"),
                data.get("location", "").strip() or None,
                data.get("purchase_date") or None,
                datetime.datetime.now().isoformat(),
                datetime.datetime.now().isoformat(),
            ),
        )
        db.commit()
        
        asset_id = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
        logger.info(f"Asset added successfully: ID {asset_id}")
        
        return jsonify({
            "message": "Asset added successfully",
            "asset_id": asset_id
        }), 201
    except Exception as e:
        logger.error(f"Failed to add asset: {e}")
        return jsonify({"error": "Failed to add asset"}), 500


@app.route("/api/assets/<int:asset_id>", methods=["PUT"])
@error_handler
def update_asset(asset_id):
    """Update an existing IT asset with validation."""
    try:
        data = request.get_json()
        
        # Validate input
        errors = validate_asset_data(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        db = get_db()
        
        # Check if asset exists
        asset = db.execute("SELECT id FROM assets WHERE id=?", (asset_id,)).fetchone()
        if not asset:
            return jsonify({"error": f"Asset with ID {asset_id} not found"}), 404
        
        db.execute(
            """UPDATE assets SET asset_name=?, asset_type=?, owner=?, status=?,
               location=?, purchase_date=?, updated_at=? WHERE id=?""",
            (
                data.get("asset_name").strip(),
                data.get("asset_type").strip(),
                data.get("owner", "").strip() or None,
                data.get("status"),
                data.get("location", "").strip() or None,
                data.get("purchase_date") or None,
                datetime.datetime.now().isoformat(),
                asset_id,
            ),
        )
        db.commit()
        logger.info(f"Asset updated successfully: ID {asset_id}")
        
        return jsonify({"message": "Asset updated successfully"}), 200
    except Exception as e:
        logger.error(f"Failed to update asset: {e}")
        return jsonify({"error": "Failed to update asset"}), 500


@app.route("/api/assets/<int:asset_id>", methods=["DELETE"])
@error_handler
def delete_asset(asset_id):
    """Delete an IT asset."""
    try:
        db = get_db()
        
        # Check if asset exists
        asset = db.execute("SELECT id FROM assets WHERE id=?", (asset_id,)).fetchone()
        if not asset:
            return jsonify({"error": f"Asset with ID {asset_id} not found"}), 404
        
        db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        db.commit()
        logger.info(f"Asset deleted successfully: ID {asset_id}")
        
        return jsonify({"message": "Asset deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Failed to delete asset: {e}")
        return jsonify({"error": "Failed to delete asset"}), 500


# ============================== Dashboard Summary ==============================
@app.route("/api/summary")
@error_handler
def summary():
    """Get dashboard summary statistics."""
    try:
        db = get_db()
        total_assets = db.execute("SELECT COUNT(*) AS c FROM assets").fetchone()["c"]
        active_assets = db.execute(
            "SELECT COUNT(*) AS c FROM assets WHERE status='Active'"
        ).fetchone()["c"]
        maintenance_assets = db.execute(
            "SELECT COUNT(*) AS c FROM assets WHERE status='Maintenance'"
        ).fetchone()["c"]
        total_alerts = db.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]
        critical_alerts = db.execute(
            "SELECT COUNT(*) AS c FROM alerts WHERE severity='Critical'"
        ).fetchone()["c"]

        return jsonify({
            "total_assets": total_assets,
            "active_assets": active_assets,
            "maintenance_assets": maintenance_assets,
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts,
        }), 200
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        return jsonify({"error": "Failed to retrieve summary"}), 500


# ============================== Error Handlers ==============================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
