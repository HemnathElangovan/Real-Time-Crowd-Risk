import time, threading, smtplib, subprocess, sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import config
from risk import RISK_MSG
from db_logger import log_alert

try:
    from twilio.rest import Client
except Exception:
    Client = None


def send_whatsapp_alert(risk, count, zone, ts):
    if Client is None:
        print("[Alert] Twilio client unavailable.")
        return None

    if not config.TWILIO_ACCOUNT_SID or not config.TWILIO_AUTH_TOKEN:
        print("[Alert] Twilio credentials missing in environment.")
        return None

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    body = (
        f"🚨 CROWD RISK ALERT\n"
        f"Risk: {risk}\n"
        f"Zone: {zone}\n"
        f"Persons: {count}\n"
        f"Time: {ts}\n"
    )
    recipient = config.WHATSAPP_RECIPIENTS[0] if config.WHATSAPP_RECIPIENTS else None
    if not recipient:
        print("[Alert] No WhatsApp recipient configured.")
        return None

    msg = client.messages.create(from_=config.TWILIO_FROM, to=recipient, body=body)
    print("Sent:", msg.sid)
    return msg.sid

class AlertSystem:
    def __init__(self, camera_id=None):
        self._last_time  = 0
        self._last_level = ""
        self._lock = threading.Lock()
        self._camera_id = camera_id
        self._twilio = None
        if config.WHATSAPP_ENABLED:
            try:
                if Client is not None and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
                    self._twilio = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
                    print("[Alert] Twilio ready.")
                else:
                    print("[Alert] Twilio unavailable or credentials missing. WhatsApp disabled.")
            except Exception as e:
                print(f"[Alert] Twilio error: {e}")

    def should_alert(self, level: str) -> bool:
        now = time.time()
        cooldown_ok  = (now - self._last_time) >= config.ALERT_COOLDOWN_SECONDS
        level_changed = level != self._last_level
        if level == "LOW":
            return False
        if getattr(config, "ALERT_ON_RISK_CHANGE", False):
            return cooldown_ok or level_changed
        return cooldown_ok

    def send(self, level: str, count: int, frame=None, zone: str = "Monitored Zone"):
        if not self.should_alert(level):
            return False
        with self._lock:
            self._last_time  = time.time()
            self._last_level = level

        snap = None
        if frame is not None:
            import cv2
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            snap = buf.tobytes()

        threading.Thread(
            target=self._dispatch,
            args=(level, count, snap, zone),
            daemon=True
        ).start()
        return True

    def _dispatch(self, level, count, snap, zone):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Alert] {level} | {count} persons | {zone} | {ts}")
        if config.EMAIL_ENABLED:    self._email(level, count, ts, snap, zone)
        if config.WHATSAPP_ENABLED and self._twilio: self._whatsapp(level, count, ts, zone)
        if config.SOUND_ENABLED:    self._sound(level)

    # ── Email ────────────────────────────────────────────────
    def _email(self, level, count, ts, snap, zone):
        try:
            colors = {"LOW": "#16a34a", "MEDIUM": "#d97706", "HIGH": "#dc2626"}
            c = colors.get(level, "#333")
            subject = f"[CROWD ALERT] {level} RISK — {count} persons | {zone} | {ts}"
            html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
  <div style="background:{c};color:#fff;padding:20px;border-radius:12px 12px 0 0;">
    <h1 style="margin:0;font-size:22px;">🚨 CROWD RISK ALERT — {level}</h1>
    <p style="margin:6px 0 0;opacity:.85;font-size:13px;">{ts}</p>
  </div>
  <div style="background:#f9f9f9;padding:24px;border-radius:0 0 12px 12px;border:1px solid #eee;">
    <p style="font-size:36px;font-weight:bold;color:{c};margin:0;">👥 {count} persons</p>
    <p style="font-size:15px;color:#333;margin:12px 0;">Zone: <b>{zone}</b></p>
    <p style="font-size:15px;color:#333;margin:12px 0;">{RISK_MSG[level]}</p>
    {"<img src='cid:snap' style='width:100%;border-radius:8px;margin-top:12px;'/>" if snap else ""}
    <p style="font-size:11px;color:#999;margin-top:16px;">Sent by Crowd Risk Detection System · YOLOv11n</p>
  </div>
</div>"""
            for r in config.EMAIL_RECIPIENTS:
                try:
                    msg = MIMEMultipart("related")
                    msg["From"] = config.EMAIL_SENDER
                    msg["To"] = r
                    msg["Subject"] = subject
                    alt = MIMEMultipart("alternative")
                    msg.attach(alt)
                    alt.attach(MIMEText(html, "html"))
                    if snap:
                        img = MIMEImage(snap, name="snap.jpg")
                        img.add_header("Content-ID", "<snap>")
                        img.add_header("Content-Disposition", "inline", filename="snap.jpg")
                        msg.attach(img)
                    with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as s:
                        s.starttls()
                        s.login(config.EMAIL_SENDER, config.EMAIL_APP_PASSWORD)
                        s.sendmail(config.EMAIL_SENDER, r, msg.as_string())
                    print(f"[Alert] Email → {r}")
                    log_alert(self._camera_id, level, "EMAIL", r, "SUCCESS")
                except Exception as e:
                    log_alert(self._camera_id, level, "EMAIL", r, "FAILED", error_message=str(e))
                    print(f"[Alert] Email recipient error ({r}): {e}")
        except Exception as e:
            print(f"[Alert] Email error: {e}")

    # ── WhatsApp ─────────────────────────────────────────────
    def _whatsapp(self, level, count, ts, zone):
        try:
            emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(level, "⚪")
            msg = (
                f"🚨🚨 *CROWD RISK ALERT* 🚨🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} *Risk Level: {level}*\n"
                f"📍 Zone: *{zone}*\n"
                f"👥 Persons detected: *{count}*\n"
                f"🕐 Time: {ts}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ {RISK_MSG[level]}\n\n"
                f"_Crowd Risk Detection System · YOLOv11n_"
            )
            for r in config.WHATSAPP_RECIPIENTS:
                try:
                    m = self._twilio.messages.create(body=msg, from_=config.TWILIO_FROM, to=r)
                    print(f"[Alert] WhatsApp → {r} | {m.sid}")
                    log_alert(self._camera_id, level, "WHATSAPP", r, "SUCCESS", message_sid=m.sid)
                except Exception as e:
                    log_alert(self._camera_id, level, "WHATSAPP", r, "FAILED", error_message=str(e))
                    print(f"[Alert] WhatsApp recipient error ({r}): {e}")
        except Exception as e:
            print(f"[Alert] WhatsApp error: {e}")

    # ── Sound ────────────────────────────────────────────────
    def _sound(self, level):
        try:
            def play():
                try:
                    sounds = {
                        "HIGH":   ["/System/Library/Sounds/Sosumi.aiff"] * 5,
                        "MEDIUM": ["/System/Library/Sounds/Ping.aiff"]   * 2,
                    }
                    files = sounds.get(level, [])
                    for f in files:
                        if sys.platform == "darwin":
                            subprocess.run(["afplay", f], capture_output=True)
                            time.sleep(0.15)
                        elif sys.platform == "win32":
                            import winsound
                            freq = 1200 if level == "HIGH" else 800
                            winsound.Beep(freq, 500)
                            time.sleep(0.2)
                        else:
                            subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"],
                                           capture_output=True)
                    log_alert(self._camera_id, level, "SOUND", "LOCAL_DEVICE", "SUCCESS")
                except Exception as e:
                    log_alert(self._camera_id, level, "SOUND", "LOCAL_DEVICE", "FAILED", error_message=str(e))
                    print(f"[Alert] Sound thread error: {e}")
            threading.Thread(target=play, daemon=True).start()
        except Exception as e:
            log_alert(self._camera_id, level, "SOUND", "LOCAL_DEVICE", "FAILED", error_message=str(e))
            print(f"[Alert] Sound error: {e}")
