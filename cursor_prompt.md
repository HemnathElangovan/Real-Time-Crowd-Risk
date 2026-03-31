# Cursor AI Prompt — Crowd Risk Detection System v2

Paste this into Cursor's AI chat to get full context:

---

I have a Real-Time Crowd Risk Detection & Emergency Alert System built with:
- **Backend**: Python + Flask (`app.py`) — runs YOLOv11n via Ultralytics, streams MJPEG video, exposes REST API at `/api/state` and `/api/snapshot`
- **ML Model**: YOLOv11n detecting COCO class 0 (person) with confidence ≥ 0.4
- **Risk logic**: LOW (0–2 persons), MEDIUM (3–4), HIGH (5+) — configurable in `config.py`
- **Alerts**: Email via Gmail SMTP, WhatsApp via Twilio, sound via macOS `afplay`
- **Frontend**: Dark tactical dashboard at `templates/index.html` — pure HTML/CSS/JS, polls `/api/state` every 800ms, streams video via `/video_feed` MJPEG, plays Web Audio API buzzer on HIGH, WhatsApp ping sound on MEDIUM
- **Files**: `config.py`, `app.py`, `detector.py`, `risk_classifier.py`, `alert_system.py`, `logger.py`, `templates/index.html`

Run with: `python app.py` → open `http://localhost:5050`

Config is in `config.py`. Camera source: 0 = MacBook webcam. Twilio credentials already set.

Help me: [YOUR REQUEST HERE]
