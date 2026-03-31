# ============================================================
#   app.py — Flask Web Server + Video Streaming Backend
#   Run: python app.py
#   Open: http://localhost:5050
# ============================================================

import cv2
import csv
import time
import threading
import os
from datetime import datetime
from flask import Flask, Response, render_template, jsonify, request

import config
from risk import classify, RISK_BGR
from alert import AlertSystem
from db_logger import (
    register_camera,
    log_crowd_event,
    save_setting,
)

app = Flask(__name__)

# ── Shared state (per camera) ────────────────────────────────
cameras_state = {
    cam["id"]: {
        "name":        cam["name"],
        "count":       0,
        "risk":        "LOW",
        "fps":         0.0,
        "connected":   False,
        "last_frame_ts": 0.0,
        "alert_fired": False,
        "alert_time":  "",
        "frame":       None,   # latest JPEG bytes
    }
    for cam in config.CAMERAS
}
history = {cam["id"]: [] for cam in config.CAMERAS}
lock = threading.Lock()
cam_cfg_to_db_id = {}


def register_all_cameras():
    """
    Register configured cameras/zones in DB.
    This should not crash app startup if DB is down.
    """
    mapping = {}
    for cam in config.CAMERAS:
        db_id = register_camera(
            camera_name=cam["name"],
            camera_source=str(cam["source"]),
            location_name=cam["name"],
        )
        mapping[cam["id"]] = db_id
        if db_id is None:
            print(f"[DB] Warning: camera '{cam['name']}' running without DB mapping.")
        else:
            print(f"[DB] Camera mapped: config_id={cam['id']} -> db_id={db_id}")
    return mapping


def detection_loop(cam_cfg: dict):
    """One thread per camera."""
    cam_id = cam_cfg["id"]
    cam_name = cam_cfg["name"]
    source = cam_cfg["source"]
    db_camera_id = cam_cfg_to_db_id.get(cam_id)

    from ultralytics import YOLO
    model = YOLO(config.MODEL_PATH)
    alerts = AlertSystem(camera_id=db_camera_id)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[Camera {cam_id}] ERROR: Cannot open {source}")
        return

    if isinstance(source, str) and source.startswith("http"):
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print(f"[Camera {cam_id}] {cam_name} — connected.")

    fps_t, fps_frames = time.time(), 0
    last_db_log_time = 0.0
    last_logged_count = None
    last_logged_risk = None

    while True:
        ret, frame = cap.read()
        if not ret:
            with lock:
                age = time.time() - cameras_state[cam_id]["last_frame_ts"]
                if age > 2.0:
                    cameras_state[cam_id]["connected"] = False
            time.sleep(0.05)
            continue

        # Detect
        results = model(
            frame,
            classes=[0],
            conf=config.CONFIDENCE_THRESHOLD,
            iou=config.IOU_THRESHOLD,
            verbose=False
        )[0]

        persons = []
        if results.boxes is not None:
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                persons.append({"bbox": [x1, y1, x2, y2], "conf": float(box.conf[0])})

        count = len(persons)
        risk = classify(count)
        color = RISK_BGR[risk]

        # Draw bboxes
        for p in persons:
            x1, y1, x2, y2 = p["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Zone label bar
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 36), (10, 10, 15), -1)
        cv2.rectangle(frame, (0, 34), (w, 36), color, -1)
        cv2.putText(
            frame,
            f"  {cam_name}  |  COUNT: {count}  |  {risk}  |  {datetime.now().strftime('%H:%M:%S')}",
            (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1, cv2.LINE_AA
        )

        # Flash border on HIGH
        if risk == "HIGH" and int(time.time() * 3) % 2 == 0:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (30, 30, 230), 4)

        # Encode JPEG
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        frame_bytes = buf.tobytes()

        # Alert — include zone name
        fired = alerts.send(risk, count, frame.copy(), zone=cam_name)

        # FPS
        fps_frames += 1
        if time.time() - fps_t >= 1.0:
            fps = round(fps_frames / (time.time() - fps_t), 1)
            fps_frames = 0
            fps_t = time.time()
        else:
            fps = cameras_state[cam_id]["fps"]

        # Update shared state
        with lock:
            cameras_state[cam_id].update({
                "count":       count,
                "risk":        risk,
                "fps":         fps,
                "connected":   True,
                "last_frame_ts": time.time(),
                "alert_fired": fired,
                "alert_time":  datetime.now().strftime("%H:%M:%S") if fired else cameras_state[cam_id]["alert_time"],
                "frame":       frame_bytes,
            })

        # Log
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/zone_{cam_id}.csv", "a", newline="") as f:
            csv.writer(f).writerow([ts, count, risk])

        history[cam_id].append({"time": ts, "count": count, "risk": risk})
        if len(history[cam_id]) > 300:
            history[cam_id].pop(0)

        # DB logging strategy:
        # write once per second OR when count/risk changes
        now = time.time()
        should_log_interval = (now - last_db_log_time) >= config.DB_EVENT_LOG_INTERVAL_SECONDS
        should_log_change = (count != last_logged_count) or (risk != last_logged_risk)
        if should_log_interval or should_log_change:
            ok = log_crowd_event(
                camera_id=db_camera_id,
                person_count=count,
                risk_level=risk,
                snapshot_path=None,
                fps=fps,
                notes=f"Zone={cam_name}",
            )
            if ok:
                last_db_log_time = now
                last_logged_count = count
                last_logged_risk = risk

    cap.release()


# ── Routes ─────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", cameras=config.CAMERAS)


@app.route("/video_feed/<int:cam_id>")
def video_feed(cam_id):
    def gen():
        while True:
            with lock:
                frame = cameras_state.get(cam_id, {}).get("frame")
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.03)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/status")
def api_status():
    with lock:
        data = {str(k): v.copy() for k, v in cameras_state.items()}
        for v in data.values():
            v.pop("frame", None)   # don't send frame bytes as JSON
            age = time.time() - float(v.get("last_frame_ts", 0.0))
            if not v.get("connected", False):
                v["health"] = "OFFLINE"
            elif age <= 2.0:
                v["health"] = "ONLINE"
            elif age <= 8.0:
                v["health"] = "RECONNECTING"
            else:
                v["health"] = "OFFLINE"
    # Compute overall risk
    risks = [v["risk"] for v in data.values()]
    overall = "HIGH" if "HIGH" in risks else "MEDIUM" if "MEDIUM" in risks else "LOW"
    return jsonify({"zones": data, "overall": overall,
                    "low_max": config.LOW_MAX, "medium_max": config.MEDIUM_MAX})


@app.route("/api/logs/<int:cam_id>")
def api_logs(cam_id):
    return jsonify(history.get(cam_id, [])[-100:])


@app.route("/api/snapshot/<int:cam_id>", methods=["POST"])
def api_snapshot(cam_id):
    """
    Save the latest frame for a specific camera.
    This endpoint is intentionally lightweight for UI-triggered snapshots.
    """
    with lock:
        frame = cameras_state.get(cam_id, {}).get("frame")
    if not frame:
        return jsonify({"ok": False, "error": "No frame available"}), 404

    os.makedirs("snapshots", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"snapshots/cam_{cam_id}_{ts}.jpg"
    try:
        with open(path, "wb") as f:
            f.write(frame)
        return jsonify({"ok": True, "path": path})
    except Exception as e:
        print(f"[Snapshot] Error saving cam {cam_id}: {e}")
        return jsonify({"ok": False, "error": "Failed to save snapshot"}), 500


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.json
    if "low_max" in data:
        config.LOW_MAX = int(data["low_max"])
        save_setting("LOW_MAX", config.LOW_MAX)
    if "medium_max" in data:
        config.MEDIUM_MAX = int(data["medium_max"])
        save_setting("MEDIUM_MAX", config.MEDIUM_MAX)
    if "sound" in data:
        config.SOUND_ENABLED = bool(data["sound"])
        save_setting("SOUND_ENABLED", config.SOUND_ENABLED)
    if "email" in data:
        config.EMAIL_ENABLED = bool(data["email"])
        save_setting("EMAIL_ENABLED", config.EMAIL_ENABLED)
    if "whatsapp" in data:
        config.WHATSAPP_ENABLED = bool(data["whatsapp"])
        save_setting("WHATSAPP_ENABLED", config.WHATSAPP_ENABLED)
    return jsonify({"ok": True})


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    os.makedirs("snapshots", exist_ok=True)

    # Camera config_id -> DB camera_id map (safe fallback if DB is unavailable)
    cam_cfg_to_db_id = register_all_cameras()

    # Persist initial thresholds in DB for reference
    save_setting("LOW_MAX", config.LOW_MAX)
    save_setting("MEDIUM_MAX", config.MEDIUM_MAX)

    # Start one thread per camera
    for cam in config.CAMERAS:
        t = threading.Thread(target=detection_loop, args=(cam,), daemon=True)
        t.start()
        print(f"[Main] Started thread for Camera {cam['id']} — {cam['name']}")
    print(f"\n[Server] Dashboard → http://localhost:{config.WEB_PORT}\n")
    app.run(host="0.0.0.0", port=config.WEB_PORT, debug=False, threaded=True)
