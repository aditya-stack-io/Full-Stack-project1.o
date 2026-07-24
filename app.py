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
"""

import sqlite3
import datetime
import psutil
from flask import Flask, jsonify, request, g, render_template

app = Flask(__name__)
DATABASE = "asset_management.db"

# ---------------------- Alert Thresholds (%) ----------------------
CPU_THRESHOLD = 80
RAM_THRESHOLD = 80
DISK_THRESHOLD = 90


# ============================== Database Helpers ==============================
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()


# ============================== Frontend Route ==============================
@app.route("/")
def index():
    return render_template("index.html")


# ============================== System Monitoring API ==============================
@app.route("/api/system-stats")
def system_stats():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = str(datetime.datetime.now() - boot_time).split(".")[0]

    stats = {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "network_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
        "network_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
        "uptime": uptime,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    }

    check_and_log_alerts(stats)
    return jsonify(stats)


def check_and_log_alerts(stats):
    """Automatically inserts an alert row whenever usage crosses a threshold."""
    db = get_db()
    triggered = []

    if stats["cpu_percent"] >= CPU_THRESHOLD:
        triggered.append((f"High CPU usage detected: {stats['cpu_percent']}%", "Critical"))
    if stats["ram_percent"] >= RAM_THRESHOLD:
        triggered.append((f"High RAM usage detected: {stats['ram_percent']}%", "Warning"))
    if stats["disk_percent"] >= DISK_THRESHOLD:
        triggered.append((f"Low disk space: {stats['disk_percent']}% used", "Critical"))

    for message, severity in triggered:
        db.execute("INSERT INTO alerts (message, severity) VALUES (?, ?)", (message, severity))
    if triggered:
        db.commit()


# ============================== Alerts API ==============================
@app.route("/api/alerts")
def get_alerts():
    db = get_db()
    rows = db.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 20").fetchall()
    return jsonify([dict(row) for row in rows])


# ============================== IT Asset Management API (CRUD) ==============================
@app.route("/api/assets", methods=["GET"])
def get_assets():
    db = get_db()
    rows = db.execute("SELECT * FROM assets ORDER BY id DESC").fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/api/assets", methods=["POST"])
def add_asset():
    data = request.get_json()
    db = get_db()
    db.execute(
        """INSERT INTO assets (asset_name, asset_type, owner, status, location, purchase_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            data.get("asset_name"),
            data.get("asset_type"),
            data.get("owner"),
            data.get("status", "Active"),
            data.get("location"),
            data.get("purchase_date"),
        ),
    )
    db.commit()
    return jsonify({"message": "Asset added successfully"}), 201


@app.route("/api/assets/<int:asset_id>", methods=["PUT"])
def update_asset(asset_id):
    data = request.get_json()
    db = get_db()
    db.execute(
        """UPDATE assets SET asset_name=?, asset_type=?, owner=?, status=?,
           location=?, purchase_date=? WHERE id=?""",
        (
            data.get("asset_name"),
            data.get("asset_type"),
            data.get("owner"),
            data.get("status"),
            data.get("location"),
            data.get("purchase_date"),
            asset_id,
        ),
    )
    db.commit()
    return jsonify({"message": "Asset updated successfully"})


@app.route("/api/assets/<int:asset_id>", methods=["DELETE"])
def delete_asset(asset_id):
    db = get_db()
    db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    db.commit()
    return jsonify({"message": "Asset deleted successfully"})


# ============================== Dashboard Summary ==============================
@app.route("/api/summary")
def summary():
    db = get_db()
    total_assets = db.execute("SELECT COUNT(*) AS c FROM assets").fetchone()["c"]
    active_assets = db.execute("SELECT COUNT(*) AS c FROM assets WHERE status='Active'").fetchone()["c"]
    maintenance_assets = db.execute("SELECT COUNT(*) AS c FROM assets WHERE status='Maintenance'").fetchone()["c"]
    total_alerts = db.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]

    return jsonify({
        "total_assets": total_assets,
        "active_assets": active_assets,
        "maintenance_assets": maintenance_assets,
        "total_alerts": total_alerts,
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
