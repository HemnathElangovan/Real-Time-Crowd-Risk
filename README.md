# Real-Time Crowd Risk Detection and Emergency Alert System

YOLO-based multi-camera crowd monitoring system with:
- Live Flask dashboard
- Risk levels (`LOW`, `MEDIUM`, `HIGH`)
- Alerts via WhatsApp, email, and sound
- MySQL storage for cameras, events, alerts, and app settings

## 1) Prerequisites

- Python 3.10+ recommended
- MySQL 8.x recommended
- pip

## 2) Install dependencies

```bash
pip install -r requirements.txt
```

## 3) Set environment variables

1. Copy example file:

```bash
cp .env.example .env
```

2. Edit `.env` and set real values:
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `EMAIL_SENDER`
- `EMAIL_APP_PASSWORD`

> Do not commit your real `.env`.

## 4) Install and prepare MySQL

### macOS (Homebrew example)

```bash
brew install mysql
brew services start mysql
```

### Create DB user/database (example)

Log in to MySQL:

```bash
mysql -u root -p
```

Then run:

```sql
CREATE DATABASE IF NOT EXISTS crowd_risk_system;
-- Optional: create dedicated user
-- CREATE USER 'crowd_user'@'localhost' IDENTIFIED BY 'strong_password';
-- GRANT ALL PRIVILEGES ON crowd_risk_system.* TO 'crowd_user'@'localhost';
FLUSH PRIVILEGES;
```

## 5) Initialize tables

Run once (safe to run multiple times):

```bash
python init_db.py
```

This creates:

1. `cameras`
   - Stores zone/camera metadata
2. `crowd_events`
   - Stores periodic detection logs (count/risk/fps/time)
3. `alert_logs`
   - Stores alert attempts (`WHATSAPP`, `EMAIL`, `SOUND`) with success/failure
4. `app_settings`
   - Stores optional key-value runtime settings

## 6) Start the app

```bash
python app.py
```

Open:

```text
http://localhost:5050
```

## 7) Logging strategy implemented

- `cameras`: registered once at startup
- `crowd_events`: logged once per second OR on count/risk change
- `alert_logs`: logged on each alert attempt (success/failure)
- `app_settings`: saved when threshold/settings are changed via dashboard API

## 8) Notes

- Dashboard routes remain compatible:
  - `/api/status`
  - `/video_feed/<cam_id>`
  - `/api/logs/<cam_id>`
- If DB is unavailable, detection/dashboard continues running and prints `[DB]` warnings.

## 9) Deploy from GitHub (Render)

This repo includes deployment files for Render:
- `Dockerfile`
- `.dockerignore`
- `render.yaml`

### Steps

1. Push latest code to GitHub.
2. In Render, create **New Web Service** from your GitHub repo.
3. Render will detect Docker automatically.
4. Set environment variables in Render dashboard:
   - `PORT=10000`
   - `WEB_PORT=10000`
   - `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
   - `WHATSAPP_RECIPIENTS`, `EMAIL_SENDER`, `EMAIL_APP_PASSWORD`
5. Deploy and open the service URL.

### Important camera note

If camera sources use private LAN IPs (for example `192.168.x.x`, `172.x.x.x`, `10.x.x.x`), a cloud host cannot access them directly.
Use publicly reachable streams, a tunnel/VPN, or deploy on a machine in the same local network as the cameras.
