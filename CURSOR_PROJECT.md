# Crowd Risk Detection System — Cursor Project

## What this project does
Real-time crowd density detection using YOLOv11n AI model from any camera
(laptop webcam or mobile phone). Classifies risk as LOW / MEDIUM / HIGH and
sends emergency alerts (Email + WhatsApp) to police officers. Includes a
live web dashboard at http://localhost:5050

## Tech stack
- Python 3.10+
- YOLOv11n (Ultralytics) — person detection
- OpenCV — video capture + frame annotation
- Flask — web server + MJPEG stream + REST API
- Twilio — WhatsApp alerts
- smtplib — Email alerts (Gmail SMTP)
- HTML/CSS/JS — live dashboard frontend

## File structure
```
crowd_risk_v2/
├── app.py          ← Main Flask server + detection loop (START HERE)
├── config.py       ← All settings (camera, thresholds, credentials)
├── detector.py     ← YOLOv11n wrapper
├── risk.py         ← Risk classification logic
├── alert.py        ← Email + WhatsApp + Sound alerts
├── templates/
│   └── index.html  ← Full live dashboard UI
├── requirements.txt
├── logs/           ← Auto-created CSV logs
└── snapshots/      ← Saved snapshots
```

## How to run
```bash
pip install -r requirements.txt
python app.py
# Open browser → http://localhost:5050
```

## Key API endpoints
- GET  /           → Dashboard UI
- GET  /video_feed → MJPEG camera stream
- GET  /api/status → Live JSON stats (count, risk, fps)
- GET  /api/logs   → Last 100 log entries
- POST /api/settings → Update thresholds/toggles live

## Config to edit before running
1. CAMERA_SOURCE in config.py (0 = laptop, "http://IP:8080/video" = phone)
2. LOW_MAX / MEDIUM_MAX for risk thresholds
3. EMAIL_ENABLED + credentials (optional)
4. WHATSAPP_ENABLED + Twilio credentials (optional)

## Sound alerts (Mac)
Uses built-in `afplay` — no install needed.
- HIGH risk   → Sosumi sound x5
- MEDIUM risk → Ping sound x2

## Cursor AI instructions
When modifying this project:
- Detection logic is in app.py → detection_loop()
- To add new alert channels, extend alert.py → _dispatch()
- To change dashboard UI, edit templates/index.html
- All thresholds and settings flow through config.py
- The /api/settings endpoint allows live config updates without restart
