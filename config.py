"""
Global configuration for the Crowd Risk Detection system.

This file is safe to commit. Secrets are loaded from environment variables.
Create a .env file locally (based on .env.example) for real credentials.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ============================================================
#   CROWD RISK DETECTION v2 — CONFIGURATION
# ============================================================

# ── Multi-Camera Sources ─────────────────────────────────────
# Keep this list structure unchanged for dashboard compatibility.
CAMERAS = [
    {
        "id": 0,
        "name": "Zone A — Main Entrance",
        "source": 0,  # laptop webcam
    },
    {
        "id": 1,
        "name": "Zone B — Central Hall",
        "source": "http://172.20.10.3:8080/video",  # phone 1
    },
    {
        "id": 2,
        "name": "Zone C — Exit Gate",
        "source": "http://172.20.10.4:8080/video",  # phone 2
    },
]

# ── YOLOv11n ─────────────────────────────────────────────────
MODEL_PATH = "yolo11n.pt"
CONFIDENCE_THRESHOLD = 0.4
IOU_THRESHOLD = 0.45

# ── Risk Thresholds ──────────────────────────────────────────
LOW_MAX = 2  # 0–2  → LOW
MEDIUM_MAX = 4  # 3–4  → MEDIUM
# 5+ → HIGH

# ── Alert behavior ────────────────────────────────────────────
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))
ALERT_ON_RISK_CHANGE = os.getenv("ALERT_ON_RISK_CHANGE", "true").lower() == "true"

# ── MySQL Database (from environment) ────────────────────────
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "crowd_risk_system")

# ── Email (Gmail) ────────────────────────────────────────────
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "your_app_password")
EMAIL_RECIPIENTS = [
    x.strip()
    for x in os.getenv("EMAIL_RECIPIENTS", "officer1@police.gov.in").split(",")
    if x.strip()
]
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# ── WhatsApp (Twilio) ────────────────────────────────────────
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "true").lower() == "true"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "whatsapp:+14155238886")
TWILIO_FROM = TWILIO_FROM_NUMBER
WHATSAPP_RECIPIENTS = [
    x.strip()
    for x in os.getenv("WHATSAPP_RECIPIENTS", "").split(",")
    if x.strip()
]

# ── Sound ────────────────────────────────────────────────────
SOUND_ALERT_ENABLED = os.getenv("SOUND_ALERT_ENABLED", "true").lower() == "true"
SOUND_ENABLED = SOUND_ALERT_ENABLED

# ── Logging ──────────────────────────────────────────────────
LOG_FILE = "logs/crowd_log.csv"
LOG_INTERVAL_SECONDS = 1
DB_EVENT_LOG_INTERVAL_SECONDS = int(os.getenv("DB_EVENT_LOG_INTERVAL_SECONDS", "1"))

# ── Web UI Server ────────────────────────────────────────────
# Supports local WEB_PORT and cloud platforms (PORT).
WEB_PORT = int(os.getenv("WEB_PORT", os.getenv("PORT", "5050")))
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "1280"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "720"))
