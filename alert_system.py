# alert_system.py — Email + WhatsApp + Sound alerts (FIXED)
import smtplib
import time
import threading
import subprocess
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

import config
from risk_classifier import RISK_MESSAGES, RISK_HEX


class AlertSystem:
    def __init__(self):
        self._last_alert_time  = 0
        self._last_alert_level = ""
        self._lock = threading.Lock()
        self._twilio = None

        if config.WHATSAPP_ENABLED:
            try:
                from twilio.rest import Client
                self._twilio = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
                print("[Alert] Twilio WhatsApp ready.")
            except ImportError:
                print("[Alert] twilio not installed — run: pip install twilio")
            except Exception as e:
                print(f"[Alert] Twilio error: {e}")

    def should_alert(self, risk_level: str) -> bool:
        now = time.time()
        cooldown_ok  = (now - self._last_alert_time) >= config.ALERT_COOLDOWN_SECONDS
        risk_changed = risk_level != self._last_alert_level
        if risk_level == "LOW":
            return False
        return cooldown_ok or risk_changed

    def send_alert(self, risk_level: str, count: int, frame=None):
        if not self.should_alert(risk_level):
            return False
        with self._lock:
            self._last_alert_time  = time.time()
            self._last_alert_level = risk_level

        snap_bytes = None
        if frame is not None:
            import cv2
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            snap_bytes = buf.tobytes()

        threading.Thread(
            target=self._dispatch,
            args=(risk_level, count, snap_bytes),
            daemon=True,
        ).start()
        return True

    def _dispatch(self, risk_level, count, snap_bytes):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Alert] {risk_level} alert — {count} persons — {ts}")

        if config.EMAIL_ENABLED:
            self._send_email(risk_level, count, ts, snap_bytes)
        if config.WHATSAPP_ENABLED and self._twilio:
            self._send_whatsapp(risk_level, count, ts)
        if config.SOUND_ALERT_ENABLED and risk_level == "HIGH":
            self._play_alarm()

    # ── EMAIL ──────────────────────────────────────────────────
    def _send_email(self, risk_level, count, ts, snap_bytes):
        try:
            color = RISK_HEX.get(risk_level, "#333")
            subject = f"[CROWD ALERT] {risk_level} RISK — {count} persons | {ts}"
            icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
            icon  = icons.get(risk_level, "⚠️")
            msg_text = RISK_MESSAGES.get(risk_level, "")

            html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
<div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;border-left:6px solid {color};">
  <div style="background:{color};color:#fff;padding:20px 24px;">
    <h1 style="margin:0;font-size:22px;">{icon} CROWD ALERT — {risk_level}</h1>
    <p style="margin:6px 0 0;opacity:.85;font-size:13px;">{ts}</p>
  </div>
  <div style="padding:24px;">
    <p style="font-size:36px;font-weight:bold;color:{color};margin:0;">👥 {count} persons</p>
    <p style="font-size:15px;color:#333;line-height:1.6;margin-top:12px;">{msg_text}</p>
    <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
    <p style="font-size:12px;color:#999;">Thresholds: LOW ≤{config.LOW_MAX} | MEDIUM ≤{config.MEDIUM_MAX} | HIGH >{config.MEDIUM_MAX}</p>
    <p style="font-size:12px;color:#999;">Crowd Risk Detection System — YOLOv11n</p>
    {"<img src='cid:snap' style='width:100%;border-radius:8px;margin-top:12px;'/>" if snap_bytes else ""}
  </div>
</div></body></html>"""

            for recipient in config.EMAIL_RECIPIENTS:
                msg = MIMEMultipart("related")
                msg["From"]    = config.EMAIL_SENDER
                msg["To"]      = recipient
                msg["Subject"] = subject
                alt = MIMEMultipart("alternative")
                msg.attach(alt)
                alt.attach(MIMEText(html, "html"))
                if snap_bytes:
                    img = MIMEImage(snap_bytes, name="snapshot.jpg")
                    img.add_header("Content-ID", "<snap>")
                    img.add_header("Content-Disposition", "inline", filename="snapshot.jpg")
                    msg.attach(img)
                with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as s:
                    s.ehlo(); s.starttls()
                    s.login(config.EMAIL_SENDER, config.EMAIL_APP_PASSWORD)
                    s.sendmail(config.EMAIL_SENDER, recipient, msg.as_string())
                print(f"[Alert] Email → {recipient}")
        except Exception as e:
            print(f"[Alert] Email error: {e}")

    # ── WHATSAPP (FIXED) ────────────────────────────────────────
    def _send_whatsapp(self, risk_level, count, ts):
        try:
            icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
            icon  = icons.get(risk_level, "⚠️")
            msg_text = RISK_MESSAGES.get(risk_level, "")

            body = (
                f"🚨🚨🚨 *EMERGENCY CROWD ALERT* 🚨🚨🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{icon} *RISK LEVEL: {risk_level}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 Persons detected: *{count}*\n"
                f"📍 Location: Monitored Zone\n"
                f"🕐 Time: {ts}\n\n"
                f"⚠️ *ACTION REQUIRED:*\n"
                f"{msg_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 _Crowd Risk Detection System_\n"
                f"_Powered by YOLOv11n AI_"
            )

            for recipient in config.WHATSAPP_RECIPIENTS:
                message = self._twilio.messages.create(
                    body=body,
                    from_=config.TWILIO_FROM_NUMBER,
                    to=recipient,
                )
                print(f"[Alert] WhatsApp → {recipient} | SID: {message.sid}")
        except Exception as e:
            print(f"[Alert] WhatsApp error: {e}")

    # ── SOUND ALARM (FIXED for Mac) ────────────────────────────
    def _play_alarm(self):
        def _beep():
            try:
                if sys.platform == "darwin":
                    # Mac — use afplay with built-in system sounds (no install needed)
                    sounds = [
                        "/System/Library/Sounds/Basso.aiff",
                        "/System/Library/Sounds/Sosumi.aiff",
                    ]
                    for _ in range(4):
                        for s in sounds:
                            subprocess.run(["afplay", s], check=False)
                            time.sleep(0.15)
                elif sys.platform == "win32":
                    import winsound
                    for _ in range(5):
                        winsound.Beep(1200, 500)
                        time.sleep(0.2)
                else:
                    for _ in range(5):
                        subprocess.run(
                            ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
                            check=False
                        )
                        time.sleep(0.3)
            except Exception as e:
                print(f"[Alert] Sound error: {e}")

        threading.Thread(target=_beep, daemon=True).start()
